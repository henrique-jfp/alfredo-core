# Módulo: Firmware (Satélites)

Este diretório contém os códigos-fonte para os dispositivos físicos (satélites) que se conectam ao Alfredo Home OS.

## Arquitetura Multi-Hardware
O servidor central do Alfredo é **agnóstico a hardware**. Ele não sabe se você está usando uma bola com tela circular, um alto-falante inteligente quadrado, ou um M5Stack.

O servidor reage exclusivamente às **Capabilities (Capacidades)** do satélite informadas no momento do registro.

## Estrutura
- `shared-protocol/`: Especificação do protocolo HTTP/WS e fluxo que QUALQUER hardware deve seguir para ser compatível com o ecossistema.
- `satellite-*`: Pastas individuais contendo o código para hardwares específicos.

Para portar o Alfredo para um novo hardware:
1. Crie uma pasta `satellite-nome-do-hardware`.
2. Implemente a lógica de rede seguindo o `shared-protocol`.
3. Pronto! Zero alteração no servidor.
