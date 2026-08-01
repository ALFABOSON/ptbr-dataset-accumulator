# Briefing — Impressão do brinquedo vórtice (sessão local)

## Contexto
Projeto de brinquedo sensorial "vórtice" em **duas cópias idênticas que se
enroscam** uma na outra pelas próprias aletas espirais (giro de ~300° até
assentar; montado forma um fuso de 8 aletas intercaladas em duas cores).
O modelo foi desenvolvido numa sessão remota do Claude Code (sem acesso à
rede local); esta sessão local assume a etapa de impressão.

## Arquivos (neste diretório `impressao_3d/`)
| Arquivo | O que é |
|---|---|
| `peca_vortice_6g_cada.stl` | A peça (imprimir **2 cópias**) — já na orientação de impressão |
| `gerar_brinquedo.py` | Gerador paramétrico (Python puro, sem dependências) — regenera o STL |
| `preview.png` | Render: peça solta ×2 e a montagem |

Branch: `claude/arquivo-impressao-3d-dfia1q` do repositório
`alfaboson/ptbr-dataset-accumulator`.

## Especificações da peça
- Altura 31,3 mm, base ø23,6 mm; montado ~37 mm.
- 4 aletas helicoidais livres por peça, miolo vazado; base flangeada.
- Folga entre as cópias: 0,35 mm no raio interno (verificada pelo script).
- Filamento estimado: **~5,4 g por cópia em PLA** (orçamento: máx. 6 g por cópia).
- Para ajustes (folga `GAP_MM`, tamanho, nº de aletas `K`, giro `TWIST`):
  editar `gerar_brinquedo.py` e rodar `python3 gerar_brinquedo.py`.

## Impressora
- Está na **rede local**, em modo **LAN Only** (nuvem desabilitada) — o envio
  tem que partir de dentro da rede.
- Printer ID exibido na tela: `0e35a229`. Modelo não confirmado; a interface
  (touch com abas Wi-Fi / Ethernet / Hotspot / Static IP / Network Mode)
  sugere Bambu Lab ou Creality. **Confirmar o modelo antes de tudo.**
- Multi-filamento: **rosa no slot 3, branco no slot 4**.

## Tarefa da sessão local
1. Confirmar que roda no Mac da rede (`uname` → `Darwin`).
2. Baixar o STL deste branch (ou clonar o repositório).
3. Descobrir a impressora na rede:
   - mDNS/Bonjour: `dns-sd -B _services._dns-sd._udp local.` e serviços
     típicos (`_bambu._tcp`, `_octoprint._tcp`, `_moonraker._tcp`);
   - Bambu Lab: portas 8883 (MQTT/TLS), 990 (FTPS), 6000; requer o
     **código de acesso LAN** exibido na tela da impressora (pedir ao usuário).
   - Creality/Klipper: Moonraker em 7125/4408, interface web em 80/4409.
4. Fatiar com o fatiador adequado ao modelo (Bambu Studio / OrcaSlicer /
   Creality Print — OrcaSlicer CLI cobre a maioria):
   - camada 0,2 mm, 2 perímetros, preenchimento 10–15 %, **sem suportes**;
   - 2 cópias em pé (orientação já correta no STL);
   - cores: uma cópia rosa (slot 3), outra branca (slot 4) — usar
     "imprimir por objeto" com filamento por objeto, ou dois trabalhos
     separados de uma cor cada;
   - conferir se o fatiador estima ≤ 6 g por cópia.
5. Enviar o trabalho pela LAN, iniciar a impressão e monitorar a 1ª camada.
6. Reportar ao usuário: peso real estimado pelo fatiador, tempo previsto e
   confirmação de que o trabalho iniciou.

## Cuidados
- Confirmar com o usuário antes de iniciar a impressão de fato.
- Se o encaixe físico ficar apertado/frouxo depois de impresso, ajustar
  `GAP_MM` no gerador (+0,1 mm afrouxa) e reimprimir só uma cópia para teste.
