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
Você é um editor de vídeo especialista em encontrar os momentos mais envolventes em vídeos para diferentes plataformas.

Aqui está uma transcrição com carimbos de tempo:

{transcript_text}

IMPORTANTE: Você deve identificar DOIS TIPOS de conteúdo:

**TIPO 1 - CLIPS CURTOS (15-60 segundos)** para YouTube Shorts, Instagram Reels e TikTok:
- Momentos que chamam atenção IMEDIATAMENTE
- Declarações impactantes ou polêmicas
- Piadas, momentos engraçados ou surpreendentes
- Revelações rápidas ou insights diretos
- Trechos autossuficientes que funcionam isoladamente
- Momentos com alta energia emocional
- Frases marcantes ou quotes memoráveis

**TIPO 2 - CORTES LONGOS (5+ minutos/300+ segundos)** para YouTube:
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
- Para clips curtos: impacto imediato é essencial
- Para clips longos: desenvolvimento e profundidade são importantes
- Evite cortes que deixem o espectador confuso sem contexto

Identifique de {min_clips} a {max_clips} momentos que atendam a esses critérios.

Formate sua resposta como JSON com esta estrutura:
{{
  "clips": [
    {{
      "start": "mm:ss",
      "end": "mm:ss",
      "reason": "breve explicação do porquê este momento é interessante",
      "caption": "legenda sugerida para o clip",
      "type": "short" ou "long",
      "platform": "YouTube Shorts/Reels/TikTok" ou "YouTube"
    }},
    ...
  ]
}}

RESPONDA APENAS COM O JSON, SEM TEXTO ADICIONAL.
"""
    
    return prompt
