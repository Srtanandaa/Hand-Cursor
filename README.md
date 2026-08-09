# HandCursor

Controle o cursor do mouse com a mao usando a camera.

## Como funciona

- O dedo indicador move o cursor.
- O controle usa a area virtual inteira do Windows, incluindo monitores extras.
- Junte o indicador e o polegar e solte para fazer um clique esquerdo simples. O cursor fica parado durante essa pinca para nao sair do alvo.
- Junte o dedo medio e o polegar e mantenha a pinca por um instante para pressionar o botao esquerdo. Mova a mao enquanto mantem a pinca para arrastar ou selecionar uma area; solte para finalizar. Uma pinca curta nao gera clique.
- Feche os quatro dedos e abra novamente para fazer um clique com o botao direito. Mantenha o polegar afastado do dedo medio: a pinça fica sempre reservada ao clique esquerdo e à seleção.
- A janela da camera mostra os pontos da mao.
- O retangulo branco na camera e a area de controle: mover o dedo dentro dele alcanca a tela inteira.
- Pressione `q` na janela da camera para sair.

## Instalar

Crie um ambiente virtual e instale as dependencias:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python download_model.py
```

Se o `mediapipe` nao instalar no Python 3.13, instale o Python 3.11 ou 3.12 e recrie o ambiente virtual com essa versao. O MediaPipe costuma liberar suporte a novas versoes do Python depois das bibliotecas principais.

## Rodar

```powershell
python hand_cursor.py
```

Na primeira execucao, o MediaPipe pode levar alguns segundos para carregar. Espere aparecer a janela da camera.

## Ajustes uteis

No arquivo `hand_cursor.py`, altere os valores em `Configuracoes`:

- `distancia_clique`: distancia maxima para considerar a pinca como clique.
- `tempo_ativacao_selecao`: tempo, em segundos, que a pinca deve ficar fechada antes de iniciar a selecao.
- `distancia_soltar`: distancia para soltar o botao depois da pinca.
- `suavizacao`: suavizacao do movimento do cursor.
- `controle_esquerda`, `controle_direita`, `controle_topo`, `controle_base`: area da camera usada para mapear a tela inteira. Diminua essa area se quiser mexer menos a mao.
- `largura_previa`: largura da janela de video para gravacao.
- `indice_camera`: troque para `1` se a camera principal nao abrir.

O PyAutoGUI tem um failsafe: mover o mouse rapidamente para o canto superior esquerdo da tela interrompe a automacao.
