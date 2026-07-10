A ideia da tool é muito boa, mas eu faria ela evoluir de uma simples "agenda" para um verdadeiro **Assistente Pessoal de Agenda**. Hoje ela parece um CRUD com notificações. O objetivo deveria ser fazer o Alfredo parecer alguém que realmente gerencia seu dia.


# 2. Eventos recorrentes ⭐⭐⭐⭐⭐

Essa é provavelmente a maior limitação.

Hoje imagino que exista apenas:

```
Evento único
```

Mas as pessoas dizem:

```
Todo sábado

Toda segunda

Todo dia

Todo mês

Todo dia 15

A cada duas semanas

Primeira sexta do mês
```

O banco deveria armazenar uma regra de recorrência (por exemplo, seguindo o padrão RRULE do iCalendar), em vez de duplicar eventos.

---



# 6. Localização

Guardar:

```
Hospital Copa D'Or
```

ou

```
Correios Flamengo
```

Depois:

```
Você precisa sair em aproximadamente 20 minutos para chegar ao compromisso no horário.
```

Integrando com Google Maps ou OSRM, isso fica muito útil.

---



---


# 11. Reagendamento por voz

Exemplo:

```
Move o dentista para quinta.
```

ou

```
Adia a reunião em 30 minutos.
```

Sem precisar excluir e criar novamente.

---

# 12. Cancelamento inteligente

Hoje:

```
Cancela o médico
```

Mas imagine:

```
Consulta

Consulta da filha

Consulta oftalmológica
```

O Alfredo deveria perguntar:

> Encontrei três compromissos. Qual deles você deseja cancelar?

---

# 13. Memória

Se você disser:

```
Tenho prova amanhã.
```

Mais tarde:

```
O que eu tenho amanhã?
```

O Alfredo deveria responder:

```
Você tem prova às 8h.
```

Mesmo sem repetir o contexto.

---

# 14. Integração com Timer

Exemplo:

```
Comecei a estudar.
```

↓

```
Cronômetro iniciado.
```

↓

```
Estudou 2h15.
```

↓

```
Associar ao evento "Estudo"?
```

Isso cria estatísticas automáticas.

---

# 15. Integração com To-do

Hoje são coisas separadas.

Mas:

```
Comprar presente

```

↓

Checklist.

Depois:

```
Comprar presente amanhã às 18h.
```

↓

Vira um compromisso.

---

# 16. Clima

Exemplo:

```
Praia amanhã 9h.
```

No dia:

```
Há previsão de chuva forte.
```

Muito útil para atividades externas.

---

# 17. Transporte

Uma hora antes:

```
Há trânsito intenso.

Recomendo sair 25 minutos antes.
```

---

# 18. Localização da casa

Você já possui o conceito de:

```
room_id
```

Isso é excelente.

Mas pode crescer.

```
Henrique criou compromisso no escritório.

↓

Aviso sai apenas no satélite do escritório.
```

Ou:

```
Está na cozinha.

↓

O satélite da cozinha fala.
```

É um diferencial interessante.

---

# 19. Persistência das notificações

Hoje você usa:

```
_notified_events
```

em memória.

Se o servidor reiniciar:

```
Todos os avisos podem ser reenviados.
```

Eu armazenaria o estado da notificação no banco (`last_notification_sent`, `notification_stage`, etc.). Assim o sistema continua consistente após reinicializações.

---
