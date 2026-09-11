# 📋 Especificação de UI/UX: *Gigabyte Monitor Controller*

Documentação funcional, técnica e de experiência do usuário para guiar redesigns, desenvolvimento de novas interfaces (ex: GTK4/Libadwaita, Qt ou Web/Electron) e evolução do produto.

---

## 1. Visão Geral do Produto

* **Nome do App:** Controle do Monitor Gigabyte GS25F2
* **Objetivo:** Permitir controle fino de hardware (brilho físico do backlight, áudio P2, calibração cromática individual e conforto visual noturno) diretamente pela interface gráfica do desktop Linux.
* **Proposta de Valor:** Eliminar a fricção de navegar pelo joystick físico e menus OSD (*On-Screen Display*) do monitor, integrando recursos que vão além do limite físico do display (como o escurecimento profundo em quarto escuro).
* **Plataforma / Ecossistema:** Linux (Fedora Workstation, GNOME / Wayland).
* **Stack Atual:** Python 3 + Tkinter (estilização personalizada com TTK).
* **Camada de Comunicação de Baixo Nível:** Protocolo DDC/CI sobre barramento I2C via cabo HDMI (`ddcutil`).

---

## 2. Design System & Identidade Visual Atual (UI)

* **Tema:** Dark Mode profundo (inspirado na paleta moderna *Catppuccin Macchiato / Mocha*).
  * **Canvas / Background Principal:** `#1E1E2E` (Evita ofuscamento em ambientes com baixa luz).
  * **Superfícies Secundárias / Cards:** `#313244` (Containers, separadores e botões inativos).
  * **Status Bar (Rodapé):** `#181825` (Área rebaixada com tipografia `#A6ADC8`).
  * **Tipografia Geral:** Sans-serif nativa do sistema em `#CDD6F4`.
* **Cores Semânticas e Acentos (*Accent Colors*):**
  * **Títulos e Hierarquia Primária:** Azul pastel (`#89B4FA`).
  * **Modo Noturno (Conforto Ocular):** Pêssego/Laranja suave (`#FAB387`).
  * **Modo Quarto Escuro:** Lavanda / Roxo claro (`#CBA6F7`).
  * **Canais de Cores Hardware:** Vermelho suave (`#EF476F`), Verde menta (`#06D6A0`) e Azul ciano (`#118AB2`).

---

## 3. Arquitetura da Informação & Wireframe Estrutural

A interface segue uma **leitura vertical linear (Single Page)** com 4 blocos funcionais separados por divisores sutis e uma barra de status no rodapé:

```text
┌──────────────────────────────────────────────────────────┐
│  [Header] Controle do Monitor Gigabyte GS25F2            │
├──────────────────────────────────────────────────────────┤
│  1. CONTROLES ESSENCIAIS                                 │
│     • Brilho (Lâmpada Backlight)   [───────O──────]  45% │
│     • Contraste                    [───────O──────]  50% │
│     • Volume P2                    [───────O──────]  30% │
├──────────────────────────────────────────────────────────┤
│  2. MODO QUARTO ESCURO                [ Desativado (OFF) ]│
│     • Atenuação Extra (Dimmer)     [───────O──────]  60% │
├──────────────────────────────────────────────────────────┤
│  3. MODO NOTURNO (LUZ AZUL)           [ Desativado (OFF) ]│
│     • Calor / Âmbar                [───────O──────]  50% │
├──────────────────────────────────────────────────────────┤
│  4. CALIBRAÇÃO DE CORES (RGB GAIN)                       │
│     • Vermelho (R)                 [───────O──────] 100  │
│     • Verde (G)                    [───────O──────] 100  │
│     • Azul (B)                     [───────O──────] 100  │
├──────────────────────────────────────────────────────────┤
│  [Status Bar] Monitor sincronizado com sucesso!          │
└──────────────────────────────────────────────────────────┘
```

---

## 4. Detalhamento Funcional & Casos de Uso (UX)

### Bloco 1: Controles Essenciais de Hardware
* **Brilho (Backlight LED):**
  * *Controle:* Slider contínuo (0 a 100%).
  * *Ação de Hardware:* Regula a intensidade de emissão dos LEDs do backlight físico do monitor (VCP `0x10`).
* **Contraste:**
  * *Controle:* Slider contínuo (0 a 100%).
  * *Ação de Hardware:* Modula a curva de separação entre tons claros e escuros gerados pelos cristais líquidos (VCP `0x12`).
* **Volume do Áudio:**
  * *Controle:* Slider contínuo (0 a 100%).
  * *Ação de Hardware:* Ajusta o ganho da saída de áudio analógica P2 localizada na traseira do monitor (VCP `0x62`).

---

### Bloco 2: Modo Quarto Escuro / Ultra Baixo (*Pitch-Black Room Mode*)
* **Dor do Usuário:** Em ambientes com iluminação completamente apagada, o nível mínimo de brilho do monitor (`0%`) ainda emite cerca de 40 a 50 nits, causando ofuscamento e fadiga visual severa.
* **Solução de Experiência:**
  * **Botão Toggle:** Ativa/Desativa o modo com 1 clique (mudança visual para estado ativo em lavanda `#CBA6F7`).
  * **Slider de Atenuação Extra (10% a 90%):** Opera como um filtro óptico digital de densidade neutra. Além de cravar a lâmpada em `0%`, fecha fisicamente a matriz de cristais líquidos (atenuando os canais RGB proporcionalmente) e reduz o contraste em harmonia.
  * **Smart Memory / Rollback:** Ao desativar o botão, o aplicativo restaura automaticamente as configurações anteriores de brilho e contraste que o usuário utilizava antes de escurecer o quarto.

---

### Bloco 3: Modo Noturno de Hardware (*Anti-Blue Light*)
* **Dor do Usuário:** Os recursos nativos de "Luz Noturna" de compositores Wayland frequentemente falham em aplicar sobre saídas secundárias HDMI/DisplayPort, ou ficam limitados a horários pré-fixados.
* **Solução de Experiência:**
  * **Botão Toggle:** Ativa/Desativa o filtro de luz azul direto no hardware do monitor.
  * **Slider Calor / Âmbar (0 a 100%):** Controla a intensidade de corte do canal Azul (indo de 100% até 15%), mantendo o Vermelho estável e o Verde equilibrado.
  * **Memória de Cores:** Ao desligar o modo, restaura a calibração de cor exata que o usuário havia definido anteriormente.

---

### Bloco 4: Calibração Fina de Cores (RGB Gain)
* **Objetivo:** Permite ao usuário fazer balanço de branco e correção de tons.
* **Heurística Invisível de UX:**
  * O firmware de fábrica do monitor Gigabyte costuma travar os canais RGB em presets fixos (ex: 6500K).
  * O aplicativo identifica essa condição de forma transparente: ao primeiro toque em qualquer slider de cor, ele chaveia o monitor para o modo **User / Custom (VCP `0x14 = 0x0b`)**, garantindo que o usuário nunca encontre controles "mortos" ou inoperantes.

---

## 5. Microinterações, Performance e Heurísticas de Nielsen

1. **Visibilidade do Estado do Sistema (Heurística #1):**
   * Barra de status no rodapé dá feedback em tempo real para cada interação: leitura inicial, envio de comando com o código hexadecimal (`VCP 0x10 = 45`) e confirmação de sucesso.
2. **Prevenção de Falhas e Proteção de Hardware (Debounce Pattern):**
   * O barramento DDC/I2C possui limites de largura de banda e as memórias do monitor não suportam rajadas de centenas de gravações por segundo.
   * O aplicativo implementa **Debounce assíncrono de 200ms**: o usuário arrasta o controle de forma suave na interface, mas o sinal de hardware só é transmitido quando o movimento desacelera ou para.
3. **Sincronização Bidirecional ao Inicializar:**
   * Ao ser iniciado, o aplicativo executa tarefas paralelas em segundo plano para consultar os valores reais armazenados no monitor, posicionando todos os sliders exatamente de acordo com o hardware físico.

---

## 6. Oportunidades de Evolução (Backlog para Designer / UI-UX)

Para uma versão 2.0 ou redesign em frameworks modernos (ex: **GTK4 + Libadwaita**):

* [ ] **Cards de Presets em 1 Clique:** Oferecer botões rápidos com perfis prontos:
  * ☀️ **Dia / Trabalho:** Brilho 60%, Cores 6500K neutras.
  * 🎮 **Jogos / FPS:** Brilho 90%, Contraste otimizado.
  * 🌙 **Leitura Noturna:** Modo Noturno 70% + Brilho 20%.
  * 🌑 **Quarto Escuro:** Modo Quarto Escuro 75% + Brilho 0.
* [ ] **Tray Icon / AppIndicator (Menu Superior do GNOME):**
  * Ícone na barra superior para alternar o Modo Noturno e Modo Quarto Escuro sem precisar manter uma janela aberta.
* [ ] **Agendamento Inteligente:**
  * Opção de ativar o modo escuro/noturno automaticamente sincronizado com o pôr do sol local.
* [ ] **Design Nativo Libadwaita:**
  * Uso de switches modernos do GNOME, cantos arredondados padronizados, ícones simbólicos SVG e suporte automático à preferência clara/escura do sistema.
