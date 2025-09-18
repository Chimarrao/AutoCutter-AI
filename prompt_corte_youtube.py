"""
Template de prompt para identificação de momentos interessantes em vídeos
"""

def get_clip_detection_prompt(transcript_text, min_clips=3, max_clips=10):
    """
    Gera o prompt otimizado para detectar tanto clips curtos quanto longos

    Args:
        transcript_text: Transcrição formatada com timestamps
        min_clips: Número mínimo de clips a serem encontrados
        max_clips: Número máximo de clips a serem encontrados

    Returns:
        String com o prompt formatado
    """

    prompt = f"""
Você é um editor de vídeo especialista em encontrar os momentos mais envolventes em vídeos para YOUTUBE.

Aqui está uma transcrição com carimbos de tempo:

{transcript_text}

IMPORTANTE: Você deve identificar UM TIPO de conteúdo:

**TIPO 1 - CORTES LONGOS (15+ minutos)** para YouTube:
- Discussões aprofundadas sobre temas específicos
- Explicações completas ou tutoriais
- Histórias longas com desenvolvimento narrativo
- Debates ou conversas estruturadas
- Análises detalhadas de assuntos complexos
- Segmentos educativos ou informativos extensos
- Momentos que precisam de contexto para serem compreendidos

CRITÉRIOS DE QUALIDADE:
- Cada clip deve ter começo, meio e fim claros
- O conteúdo deve ser envolvente do primeiro ao último segundo
- Para clips longos: desenvolvimento e profundidade são importantes
- Evite cortes que deixem o espectador confuso sem contexto

Formate sua resposta como JSON com esta estrutura:
{{
  "clips": [
    {{
      "start": "mm:ss",
      "end": "mm:ss",
      "caption": "legenda sugerida para o clip",
    }},
    ...
  ]
}}

RESPONDA APENAS COM O JSON, SEM TEXTO ADICIONAL.
"""

    return prompt

def get_summary_prompt(transcript_text, target_duration_minutes=30):
    """
    Gera o prompt para criar um resumo do vídeo com os melhores momentos aglutinados

    Args:
        transcript_text: Transcrição formatada com timestamps
        target_duration_minutes: Duração alvo do resumo em minutos (padrão: 30)

    Returns:
        String com o prompt formatado para resumo
    """

    prompt = f"""
Você é um editor de vídeo especialista em criar RESUMOS CONDENSADOS para YouTube.

Aqui está uma transcrição com carimbos de tempo:

{transcript_text}

OBJETIVO: Criar um resumo condensado com os MELHORES MOMENTOS do vídeo original.

CRITÉRIOS PARA SELEÇÃO:
- Identifique os momentos mais valiosos, informativos e envolventes
- Priorize conteúdo que seja autocontido e compreensível
- Mantenha a sequência cronológica quando possível
- Evite redundâncias e repetições
- Foque em insights, conclusões importantes e momentos de maior impacto
- Mantenha transições naturais entre os segmentos, como cortes feitos por um editor

INSTRUÇÕES ESPECIAIS:
- EVITE sobreposição de trechos entre cortes consecutivos
- GARANTA que o final de um corte e o início do próximo não contenham frases ou palavras repetidas
- PREFIRA cortes com bordas limpas e naturais na fala (ex: pausas, troca de assunto ou mudança de tom)
- Se necessário, ajuste ligeiramente o tempo de início ou fim para remover repetições

TIPOS DE MOMENTOS PRIORITÁRIOS:
- Explicações chave e conceitos importantes
- Histórias marcantes e exemplos práticos
- Conclusões e insights valiosos
- Momentos emocionais ou inspiradores
- Informações exclusivas ou revelações
- Dicas práticas e aplicáveis

INSTRUÇÕES:
1. Priorize qualidade sobre quantidade
2. Mantenha a essência e mensagem principal do vídeo original

Formate sua resposta como JSON com esta estrutura:
{{
  "summary_type": "condensed_highlights",
  "clips": [
    {{
      "start": "mm:ss",
      "end": "mm:ss",
      "caption": "descrição do momento",
      "importance": "alta|média|baixa",
      "reason": "por que este momento é importante"
    }},
    ...
  ]
}}

RESPONDA APENAS COM O JSON, SEM TEXTO ADICIONAL.
"""

    return prompt
