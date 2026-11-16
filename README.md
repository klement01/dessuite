# dessuite

Conjunto de ferramentas para trabalhar com Sistemas a Eventos Discretos (DES, _Discrete Event Systems_).

## Instalação

Verifique que o [Python 3.14.3 ou superior](https://www.python.org/) esteja instalado, e que o comando `pip` ou `python` estejam disponíveis no terminal.

[Clone o repositório](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository) através do terminal usando o git ou através do navegador. Então, navegue para o diretório do repositório e instale o módulo dessuite usando o pip:

```shell
git clone https://github.com/klement01/dessuite
cd dessuite
pip install .
# Alternativa: python -m pip install .
```

Após instalar o módulo, o comando `dessuite` deve ficar disponível no terminal.

## Ferramentas

Após instalar o módulo dessuite, as ferramentas descritas abaixo devem ficar disponíveis no terminal através do comando `dessuite`, no formato:

```shell
dessuite {'nome do comando'} ['argumentos'...]
```

### dessuite controller

Controla uma planta do [FlexFact](https://fgdes.tf.fau.de/flexfact.html) usando controladores especificados como Autômatos Finitos Determinísticos (DFA, _Deterministic Finite Automata_) ou Redes de Petri. Se comunica com a planta usando Modbus/TCP.

O comando `dessuite controller` requer como entradas:

- Um arquivo _Modbus Device File_ (**.dev**) gerado pelo FlexFact. Este arquivo define o protocolo de comunicação utilizado entre o FlexFact e o dessuite.
    - Para gerar este arquivo, abra o arquivo da planta a ser controlada (.ffs) no FlexFact e selecione "File" → "Export Modbus/TCP configuration".
- Um ou mais arquivos de especificação de controladores. Os formatos aceitos são:
    - **.gen**: DFA; gerado pelo FAUDES/DESTool.
    - **.net**: Rede de Petri; gerado pelo Tina Toolbox.
        - Para gerar este arquivo, abra o arquivo gráfico do Tina Toolbox (.ndr) da Rede de Petri a ser usada e selecione "Edit" → "textify".

Caso sejam especificados múltiplos controladores (DFAs e/ou Redes de Petri), os controladores são executados em paralelo seguindo a metodologia de controle supervisório modular local. Veja ["Controle supervisório modular de sistemas de manufatura" por Max H. de Queiroz, José E. R. Cury (2002)](https://www.scielo.br/j/ca/a/CmNVyYqYLMHkcGyMzjkfDTG/?lang=pt) para mais informações.

#### Exemplo

Para controlar uma planta usando uma Rede de Petri:

1. Siga os passos acima para gerar o arquivo **.dev** e o arquivo **.net**.
1. No FlexFact, selecione "Simulation" → "Modbus" para selecionar o protocolo de comunicação Modbus.
1. No FlexFact, selecione "Start" para iniciar a simulação.
1. No terminal, navegue para o diretório contendo os arquivos gerados e execute o controlador. Assumindo que os arquivos se chamam Modbus.dev e Controlador.net, o comando a ser executado é:
    ```shell
    dessuite controller Modbus.dev Controlador.net
    ```
1. Aguarde a mensagem: "_Connected!_".

### dessuite generator

Gera um conjunto de arquivos de código em C que implementam uma Rede de Petri usando FreeRTOS para uso em microcontroladores.

A Rede de Petri pode se comunicar com o mundo externo de várias formas, implementadas como módulos da ferramenta de geração em **dessuite/generator_tools/modules**. Os módulos disponíveis são:

- **hal_gpio**: mapeia eventos para portas digitais do microcontrolador usando a interface HAL (_Hardware Abstraction Layer_). Não realiza a configuração inicial das portas digitais; a configuração inicial deve ser feita manualmente ou usando outra ferramente de geração de código específica para o microcontrolador, como o [STM32CubeMX](https://www.st.com/en/development-tools/stm32cubemx.html) para microcontroladores da STMicroelectronics.
- **hal_uart**: mapeia eventos para mensagens enviadas e recebidas por UART usando a interface HAL (_Hardware Abstraction Layuer_). Não realiza a configuração inicial do UART.

O mapeamento de eventos da Rede de Petri para entradas e saídas do microcontrolador e especificações de alguns outros parâmetros são feitos através de um arquivo em um formato proprietário do **dessuite**, com extensão recomendada **.des.xml**.

O comando `dessuite generator` requer como entradas:

- Um arquivo textual de especificação de Rede de Petri gerado pelo Tina Toolbox (**.net**).
- Um arquivo de especificação geração no formato proprietário do **dessuite** (**.des.xml**).
- O caminho no qual o arquivo de código fonte em C (**.c**) será salvo.
- O caminho no qual o arquivo _header_ em C (**.c**) será salvo.

A função `DesControllerSetup` deve ser chamada antes da inicialização do kernel do FreeRTOS (antes da chamada de `osKernelStart`).

## Exemplos

Alguns exemplos de uso do **dessuite** estão disponíveis no diretório **examples**.

### flectfact_controller

Um projeto simples baseado no controlador STM32F103C6T6 para ilustrar o funcionamento básico do `dessuite generator`. A maioria dos arquivos foram gerados automaticamente pelo STM32CubeMX usando o projeto **flectfact_controller.ioc**. As especificações do controlador no diretório **ControllerSpec** foram feitos manualmente. Os arquivos **Src\des_controller.c** e **Inc\des_controller.h** foram gerados pelo `dessuite generator` usando as especificações do controlador. Os arquivos CMakeLists.txt e Src\main.c, gerados pelo STM32CubeMX, foram manualmente modificados para integrar os arquivos gerados pelo `dessuite generator`.

A pinagem foi definida no arquivo de projeto **simple_arm_project.ioc**, que é usado pelo STM32CubeMX para gerar o código de inicialização do microcontrolador.

O controlador foi definido no arquivo **ControllerSpec/Controller.ndr**, e convertido para o formato textual em **ControllerSpec/Controller.net**.

Os arquivos **Src/des_controller.c** e **Inc/des_controller.h** foram gerados com o seguinte comando, executado no diretório raiz do exemplo (**exaples/flexfact_controller**):

`dessuite generator ControllerSpec\Controller.net ControllerSpec\IOMap.des.xml Src\des_controller.c Inc\des_controller.h`

O arquivo **des_controller.c** foi incluído manualmente no arquivo **CMakeLists.txt** gerado pelo STM32CubeMX. O `#include "des_controller.h"` e a chamada da função `DesControllerSetup` foram incluídos manualmente no arquivo **Src\main.c** gerado pelo STM32CubeMX.

Para usar o exemplo, o diretório raiz do exemplo (**exaples/flexfact_controller**) deve ser aberto diretamente no VS Code, ou seja, ele deve ser a raiz do VS Code. Então, o projeto pode ser compilado e programado em um microcontrolador STM32F103C6T6 usando a [extensão STM32CubeIDE do VS Code](https://marketplace.visualstudio.com/items?itemName=stmicroelectronics.stm32-vscode-extension). Tutorial oficial da extensão STM32CubeIDE: [Get started with STM32Cube for VS Code: from installation to debugging](https://youtu.be/aWMni01XGeI?si=-qLbvPUFsaDjYtpp).
