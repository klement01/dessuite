# dessuite

Conjunto de ferramentas para trabalhar com Sistemas a Eventos Discretos (DES, _Discrete Event Systems_).

## Instalação

Verifique que o [Python 3.14.3 ou superior](https://www.python.org/) esteja instalado, e que o comando `pip` ou `python` estejam disponíveis no terminal.

[Clone o repositório](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository) através do terminal usando o **git** ou através do navegador. Então, navegue para o diretório do repositório e instale o módulo **dessuite** usando o **pip**:

```shell
git clone https://github.com/klement01/dessuite
cd dessuite
pip install .
# Alternativa: python -m pip install .
```

Após instalar o módulo, o comando `dessuite` deve ficar disponível no terminal.



## Ferramentas

Após instalar o módulo `dessuite`, as ferramentas descritas abaixo devem ficar disponíveis no terminal através do comando `dessuite`, no formato:

```shell
dessuite {'nome do comando'} ['argumentos'...]
```

### dessuite controller

Permite controlar uma planta do [FlexFact](https://fgdes.tf.fau.de/flexfact.html) através do comunicação Modbus/TCP usando controladores especificados como Autômatos Finitos Determinísticos (DFA, _Deterministic Finite Automata_) ou Redes de Petri.

O comando `dessuite controller` requer como entradas:

- Um arquivo _Modbus Device File_ (**.dev**) gerado pelo FlexFact. Este arquivo define o protocolo de comunicação utilizado entre o FlexFact e o `dessuite`.
    - Para gerar este arquivo, abra o arquivo da planta a ser controlada (.ffs) no FlexFact e selecione "File" → "Export Modbus/TCP configuration".
- Um ou mais arquivos de especificação de controladores. Os formatos aceitos são:
    - **.gen**: DFA; gerado pelo FAUDES/DESTool.
    - **.net**: Rede de Petri; gerado pelo Tina Toolbox.
        - Para gerar este arquivo, abra o arquivo gráfico do Tina Toolbox (.ndr) da Rede de Petri a ser usada e selecione "Edit" → "textify".

Caso sejam especificados múltiplos controladores (DFAs e/ou Redes de Petri), os controladores são executados em paralelo seguindo a metodologia de controle supervisório modular local. Veja ["Controle supervisório modular de sistemas de manufatura" por Max H. de Queiroz, José E. R. Cury (2002)](https://www.scielo.br/j/ca/a/CmNVyYqYLMHkcGyMzjkfDTG/?lang=pt) para mais informações.

#### Exemplo

Para controlar uma planta usando uma Rede de Petri:

1. Siga os passos acima para gerar o arquivo **dev** e o arquivo **net**.
1. No FlexFact, selecione "Simulation" → "Modbus" para selecionar o protocolo de comunicação Modbus.
1. No FlexFact, selecione "Start" para iniciar a simulação.
1. No terminal, navegue para o diretório contendo os arquivos gerados e execute o controlador. Assumindo que os arquivos se chamam Modbus.dev e Controlador.net, o comando a ser executado é:
    ```shell
    dessuite controller Modbus.dev Controlador.net
    ```
1. Aguarde a mensagem: "_Connected!_".
