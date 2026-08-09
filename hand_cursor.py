from __future__ import annotations

import math
import os
import platform
import time
from dataclasses import dataclass
from pathlib import Path

PASTA_MATPLOTLIB = Path(__file__).with_name(".matplotlib")
PASTA_MATPLOTLIB.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(PASTA_MATPLOTLIB))
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

CAMINHO_MODELO = Path(__file__).with_name("models") / "hand_landmarker.task"
TITULO_JANELA = "Hand Cursor - Preview"



@dataclass(frozen=True)
class Configuracoes:
    indice_camera: int = 0
    suavizacao: float = 0.58
    distancia_clique: float = 0.075
    distancia_soltar: float = 0.105
    tempo_ativacao_selecao: float = 0.25
    confianca_deteccao: float = 0.7
    confianca_rastreamento: float = 0.7
    largura_camera: int = 640
    altura_camera: int = 480
    fps_camera: int = 30
    largura_previa: int = 960
    controle_esquerda: float = 0.18
    controle_direita: float = 0.82
    controle_topo: float = 0.14
    controle_base: float = 0.86


def interpolar(atual: float, alvo: float, quantidade: float) -> float:
    return atual + (alvo - atual) * quantidade


def limitar(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))


def mapear_intervalo(
    valor: float,
    origem_minima: float,
    origem_maxima: float,
    destino_minimo: float,
    destino_maximo: float,
) -> float:
    valor = limitar(valor, origem_minima, origem_maxima)
    tamanho_origem = origem_maxima - origem_minima
    tamanho_destino = destino_maximo - destino_minimo
    return destino_minimo + ((valor - origem_minima) / tamanho_origem) * tamanho_destino


def mapear_mao_para_tela(ponta_indicador, largura_tela: int, altura_tela: int, config: Configuracoes):
    x = mapear_intervalo(
        ponta_indicador.x,
        config.controle_esquerda,
        config.controle_direita,
        0,
        largura_tela - 1,
    )
    y = mapear_intervalo(
        ponta_indicador.y,
        config.controle_topo,
        config.controle_base,
        0,
        altura_tela - 1,
    )
    return x, y


def obter_limites_da_tela(pyautogui):
    if platform.system() == "Windows":
        import ctypes

        user32 = ctypes.windll.user32
        esquerda = user32.GetSystemMetrics(76)
        topo = user32.GetSystemMetrics(77)
        largura = user32.GetSystemMetrics(78)
        altura = user32.GetSystemMetrics(79)
        return esquerda, topo, largura, altura

    largura, altura = pyautogui.size()
    return 0, 0, largura, altura


def distancia_entre_pontos(a, b) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def esta_em_pinca(ponta_dedo, ponta_polegar, config: Configuracoes, mouse_pressionado: bool) -> bool:
    distancia = distancia_entre_pontos(ponta_dedo, ponta_polegar)
    limite = config.distancia_soltar if mouse_pressionado else config.distancia_clique
    return distancia < limite


def mao_esta_fechada(pontos_mao) -> bool:
    """Reconhece um punho fechado, usado para o clique direito."""
    pulso = pontos_mao[0]
    pares_dedos = ((8, 6), (12, 10), (16, 14), (20, 18))
    dedos_fechados = 0

    for indice_ponta, indice_junta in pares_dedos:
        ponta = pontos_mao[indice_ponta]
        junta = pontos_mao[indice_junta]
        ponta_abaixo_da_junta = ponta.y > junta.y
        ponta_perto_da_palma = distancia_entre_pontos(ponta, pulso) < distancia_entre_pontos(junta, pulso) * 1.15

        if ponta_abaixo_da_junta or ponta_perto_da_palma:
            dedos_fechados += 1

    return dedos_fechados >= 4


def carregar_dependencias():
    print("Carregando OpenCV...", flush=True)
    import cv2

    print("Carregando MediaPipe... pode demorar alguns segundos na primeira vez.", flush=True)
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python.vision import (
        HandLandmarker,
        HandLandmarkerOptions,
        HandLandmarksConnections,
        RunningMode,
    )

    print("Carregando controle do mouse...", flush=True)
    import pyautogui

    return (
        cv2,
        mp,
        BaseOptions,
        HandLandmarker,
        HandLandmarkerOptions,
        HandLandmarksConnections,
        RunningMode,
        pyautogui,
    )


def desenhar_area_de_controle(cv2, quadro, config: Configuracoes) -> None:
    altura, largura, _ = quadro.shape
    canto_superior_esquerdo = (
        int(config.controle_esquerda * largura),
        int(config.controle_topo * altura),
    )
    canto_inferior_direito = (
        int(config.controle_direita * largura),
        int(config.controle_base * altura),
    )
    cv2.rectangle(quadro, canto_superior_esquerdo, canto_inferior_direito, (255, 255, 255), 1)


def redimensionar_previa(cv2, quadro, largura_previa: int):
    altura, largura, _ = quadro.shape
    altura_previa = int(altura * (largura_previa / largura))
    return cv2.resize(quadro, (largura_previa, altura_previa))


def criar_detector_de_mao(
    BaseOptions,
    HandLandmarker,
    HandLandmarkerOptions,
    RunningMode,
    config: Configuracoes,
):
    if not CAMINHO_MODELO.exists():
        raise FileNotFoundError(
            "Modelo da mao nao encontrado. Rode: "
            ".\\.venv\\Scripts\\python.exe download_model.py"
        )

    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(CAMINHO_MODELO)),
        running_mode=RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=config.confianca_deteccao,
        min_hand_presence_confidence=config.confianca_deteccao,
        min_tracking_confidence=config.confianca_rastreamento,
    )
    return HandLandmarker.create_from_options(options)


def desenhar_mao(cv2, quadro, pontos_mao, conexoes) -> None:
    altura, largura, _ = quadro.shape

    for conexao in conexoes:
        inicio = pontos_mao[conexao.start]
        fim = pontos_mao[conexao.end]
        ponto_inicio = (int(inicio.x * largura), int(inicio.y * altura))
        ponto_fim = (int(fim.x * largura), int(fim.y * altura))
        cv2.line(quadro, ponto_inicio, ponto_fim, (35, 190, 95), 2)

    for ponto_mao in pontos_mao:
        ponto = (int(ponto_mao.x * largura), int(ponto_mao.y * altura))
        cv2.circle(quadro, ponto, 4, (255, 255, 255), -1)


def principal() -> None:
    (
        cv2,
        mp,
        BaseOptions,
        HandLandmarker,
        HandLandmarkerOptions,
        HandLandmarksConnections,
        RunningMode,
        pyautogui,
    ) = carregar_dependencias()

    config = Configuracoes()
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0
    pyautogui.MINIMUM_DURATION = 0
    pyautogui.MINIMUM_SLEEP = 0
    tela_esquerda, tela_topo, largura_tela, altura_tela = obter_limites_da_tela(pyautogui)

    camera = cv2.VideoCapture(config.indice_camera)
    if not camera.isOpened():
        raise RuntimeError("Nao foi possivel abrir a camera.")

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, config.largura_camera)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, config.altura_camera)
    camera.set(cv2.CAP_PROP_FPS, config.fps_camera)
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    cv2.namedWindow(TITULO_JANELA, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(TITULO_JANELA, config.largura_previa, 720)
    try:
        cv2.setWindowProperty(TITULO_JANELA, cv2.WND_PROP_TOPMOST, 1)
    except cv2.error:
        pass

    detector_mao = criar_detector_de_mao(
        BaseOptions,
        HandLandmarker,
        HandLandmarkerOptions,
        RunningMode,
        config,
    )

    mouse_x = tela_esquerda + (largura_tela / 2)
    mouse_y = tela_topo + (altura_tela / 2)
    pinca_de_clique_direito_estava_ativa = False
    pinca_de_clique_esquerdo_estava_ativa = False
    mouse_esta_pressionado = False
    inicio_pinca_selecao: float | None = None

    try:
        while True:
            camera_ok, quadro = camera.read()
            if not camera_ok:
                break

            quadro = cv2.flip(quadro, 1)
            altura, largura, _ = quadro.shape
            rgb = cv2.cvtColor(quadro, cv2.COLOR_BGR2RGB)
            imagem = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            tempo_ms = int(time.monotonic() * 1000)
            resultado = detector_mao.detect_for_video(imagem, tempo_ms)

            if resultado.hand_landmarks:
                pontos_mao = resultado.hand_landmarks[0]
                ponta_indicador = pontos_mao[8]
                ponta_medio = pontos_mao[12]
                ponta_polegar = pontos_mao[4]

                pinca_ativa = esta_em_pinca(
                    ponta_medio,
                    ponta_polegar,
                    config,
                    mouse_esta_pressionado,
                )
                pinca_de_clique_esquerdo_ativa = esta_em_pinca(
                    ponta_indicador,
                    ponta_polegar,
                    config,
                    pinca_de_clique_esquerdo_estava_ativa,
                )
                # A pinça é sempre reservada ao botão esquerdo/seleção.
                # Para o clique direito, feche os quatro dedos sem encostar o
                # polegar na ponta do indicador.
                gesto_clique_direito = mao_esta_fechada(pontos_mao) and not pinca_ativa

                if gesto_clique_direito:
                    if mouse_esta_pressionado:
                        pyautogui.mouseUp(button="left")
                        mouse_esta_pressionado = False

                    pinca_de_clique_direito_estava_ativa = True
                    pinca_de_clique_esquerdo_estava_ativa = False
                    inicio_pinca_selecao = None
                elif pinca_de_clique_direito_estava_ativa and not gesto_clique_direito:
                    pyautogui.click(button="right")
                    pinca_de_clique_direito_estava_ativa = False
                else:
                    if pinca_ativa:
                        pinca_de_clique_esquerdo_estava_ativa = False
                        alvo_x, alvo_y = mapear_mao_para_tela(
                            ponta_indicador,
                            largura_tela,
                            altura_tela,
                            config,
                        )
                        alvo_x += tela_esquerda
                        alvo_y += tela_topo
                        mouse_x = interpolar(mouse_x, alvo_x, config.suavizacao)
                        mouse_y = interpolar(mouse_y, alvo_y, config.suavizacao)
                        pyautogui.moveTo(mouse_x, mouse_y, duration=0)

                        if inicio_pinca_selecao is None:
                            inicio_pinca_selecao = time.monotonic()
                        elif (
                            not mouse_esta_pressionado
                            and time.monotonic() - inicio_pinca_selecao >= config.tempo_ativacao_selecao
                        ):
                            pyautogui.mouseDown(button="left")
                            mouse_esta_pressionado = True
                    elif mouse_esta_pressionado:
                        inicio_pinca_selecao = None
                        pyautogui.mouseUp(button="left")
                        mouse_esta_pressionado = False
                        pinca_de_clique_esquerdo_estava_ativa = False
                    elif pinca_de_clique_esquerdo_ativa:
                        # Congela o cursor durante a pinça de clique simples.
                        inicio_pinca_selecao = None
                        pinca_de_clique_esquerdo_estava_ativa = True
                    elif pinca_de_clique_esquerdo_estava_ativa:
                        pyautogui.click(button="left")
                        pinca_de_clique_esquerdo_estava_ativa = False
                    else:
                        inicio_pinca_selecao = None
                        alvo_x, alvo_y = mapear_mao_para_tela(
                            ponta_indicador,
                            largura_tela,
                            altura_tela,
                            config,
                        )
                        alvo_x += tela_esquerda
                        alvo_y += tela_topo
                        mouse_x = interpolar(mouse_x, alvo_x, config.suavizacao)
                        mouse_y = interpolar(mouse_y, alvo_y, config.suavizacao)
                        pyautogui.moveTo(mouse_x, mouse_y, duration=0)

                desenhar_mao(
                    cv2,
                    quadro,
                    pontos_mao,
                    HandLandmarksConnections.HAND_CONNECTIONS,
                )

                indicador_x = int(ponta_indicador.x * largura)
                indicador_y = int(ponta_indicador.y * altura)
                medio_x = int(ponta_medio.x * largura)
                medio_y = int(ponta_medio.y * altura)
                polegar_x = int(ponta_polegar.x * largura)
                polegar_y = int(ponta_polegar.y * altura)
                cor_linha = (35, 190, 95) if mouse_esta_pressionado else (255, 210, 60)
                cor_linha = (80, 80, 255) if gesto_clique_direito else cor_linha
                cv2.circle(quadro, (indicador_x, indicador_y), 9, (255, 210, 60), -1)
                cv2.circle(quadro, (medio_x, medio_y), 9, (255, 210, 60), -1)
                cv2.circle(quadro, (polegar_x, polegar_y), 9, (255, 210, 60), -1)
                cv2.line(quadro, (medio_x, medio_y), (polegar_x, polegar_y), cor_linha, 3)
                if gesto_clique_direito:
                    cv2.putText(
                        quadro,
                        "Punho sem pinca: abra para clique direito",
                        (20, 35),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (80, 80, 255),
                        2,
                    )
            elif mouse_esta_pressionado:
                pyautogui.mouseUp()
                mouse_esta_pressionado = False
                pinca_de_clique_direito_estava_ativa = False
                pinca_de_clique_esquerdo_estava_ativa = False
                inicio_pinca_selecao = None
            elif pinca_de_clique_direito_estava_ativa:
                # Sem mao visivel nao ha uma abertura intencional do punho.
                pinca_de_clique_direito_estava_ativa = False
                pinca_de_clique_esquerdo_estava_ativa = False
                inicio_pinca_selecao = None

            desenhar_area_de_controle(cv2, quadro, config)
            previa = redimensionar_previa(cv2, quadro, config.largura_previa)
            cv2.imshow(TITULO_JANELA, previa)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        if mouse_esta_pressionado:
            pyautogui.mouseUp()
        detector_mao.close()
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    principal()
