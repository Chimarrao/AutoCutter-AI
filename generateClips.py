import os
import subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import json
import whisper
import requests
import argparse
import textwrap
import google.generativeai as genai
from prompt_corte_youtube import get_clip_detection_prompt

# Importa o módulo json no nível do módulo para evitar problemas de escopo
import json as json_module

# Opções de API LLM gratuitas - usaremos a API Google Gemini com limite de uso para o plano gratuito
# Alternativas incluem a HuggingFace Inference API ou outros serviços gratuitos
# Você pode trocar esta implementação por qualquer outra API LLM gratuita
class LLMClipFinder:
    """Classe para lidar com chamadas à API LLM para identificar trechos interessantes"""

    def __init__(self, api_key=None, model="gemini-2.0-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model

        if not self.api_key:
            print("Nenhuma chave de API do Google Gemini encontrada. Alternando para método alternativo.")
            self.use_gemini = False
            return
            
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            self.use_gemini = True
        except Exception as e:
            print(f"Falha ao inicializar a API Gemini: {e}")
            self.use_gemini = False

    def find_interesting_moments(self, transcription_segments, min_clips=3, max_clips=10):
        """Use LLM para identificar momentos interessantes a partir de segmentos de transcrição"""

        # Formata os dados da transcrição para o LLM
        transcript_text = ""
        for i, segment in enumerate(transcription_segments):
            start_time = self._format_time(segment["start"])
            end_time = self._format_time(segment["end"])
            transcript_text += f"[{start_time} - {end_time}] {segment['text']}\n"

        # Usa o prompt do arquivo separado
        prompt = get_clip_detection_prompt(transcript_text, min_clips, max_clips)

        if self.use_gemini:
            return self._call_gemini_api(prompt)
        else:
            return self._fallback_extraction(transcription_segments)
            
    def _call_gemini_api(self, prompt):
        """Chama a API Gemini com tratamento de erros adequado"""
        try:
            response = self.model.generate_content(prompt)
            content = response.text
            
            # Tenta analisar o JSON da resposta
            try:
                # Encontra o JSON na resposta se não for um JSON puro
                import re
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    content = json_match.group(0)
                
                import json
                clip_data = json.loads(content)
                return clip_data
            except json.JSONDecodeError:
                print("Falha ao analisar o JSON da resposta do LLM. Usando extração manual.")
                return self._manually_extract_clips(content)
                
        except Exception as e:
            print(f"Erro ao chamar a API Gemini: {str(e)}")
            return self._fallback_extraction([])  # Passa uma lista vazia como fallback
    def _manually_extract_clips(self, content):
        """Extrai informações do clipe manualmente se a análise do JSON falhar"""
        clips = []
        
        # Tenta encontrar e extrair informações do clipe usando regex
        import re
        
        # Procura por padrões como "Start: 01:23" ou "Start time: 01:23"
        start_times = re.findall(r'start(?:\s+time)?:\s*(\d+:\d+)', content, re.IGNORECASE)
        end_times = re.findall(r'end(?:\s+time)?:\s*(\d+:\d+)', content, re.IGNORECASE)
        
        # Extrai tudo entre "Reason:" e a próxima seção como o motivo
        reasons = re.findall(r'reason:\s*(.*?)(?=\n\s*(?:caption|start|end|clip|\d+\.)|\Z)',
                             content, re.IGNORECASE | re.DOTALL)
        
        # Extrai legendas
        captions = re.findall(r'caption:\s*(.*?)(?=\n\s*(?:reason|start|end|clip|\d+\.)|\Z)',
                              content, re.IGNORECASE | re.DOTALL)
        
        # Combina as informações extraídas
        for i in range(min(len(start_times), len(end_times))):
            clip = {
                "start": start_times[i],
                "end": end_times[i],
                "reason": reasons[i].strip() if i < len(reasons) else "Momento interessante",
                "caption": captions[i].strip() if i < len(captions) else "Confira este momento!"
            }
            clips.append(clip)
        
        return {"clips": clips}
    
    def _fallback_extraction(self, transcription_segments):
        """Método de fallback simples se todas as chamadas da API falharem"""
        clips = []
        
        # Agrupa segmentos em clipes potenciais (abordagem simples)
        # Este é um fallback muito básico que apenas seleciona segmentos espaçados uniformemente
        total_segments = len(transcription_segments)
        num_clips = min(5, total_segments // 3)  # Cria até 5 clipes

        if num_clips == 0 and total_segments > 0:
            num_clips = 1
        
        for i in range(num_clips):
            idx = (i * total_segments) // num_clips
            segment = transcription_segments[idx]
            
            # Calcula o início/fim do clipe (visando clipes de 45-60 segundos)
            clip_mid = (segment["start"] + segment["end"]) / 2
            clip_start = max(0, clip_mid - 25)
            clip_end = min(clip_mid + 25, segment["end"] + 30)
            
            clip = {
                "start": self._format_time(clip_start),
                "end": self._format_time(clip_end),
                "reason": "Segmento potencialmente interessante",
                "caption": segment["text"][:100] + "..." if len(segment["text"]) > 100 else segment["text"]
            }
            clips.append(clip)
        
        return {"clips": clips}
    
    def _format_time(self, seconds):
        """Formata os segundos no formato mm:ss"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"


def extract_audio(video_path, output_path="temp_audio.wav"):
    """Extrai o áudio do arquivo de vídeo"""
    command = f"ffmpeg -i {video_path} -ab 160k -ac 2 -ar 44100 -vn {output_path} -y"
    subprocess.call(command, shell=True)
    return output_path


def transcribe_audio(audio_path, whisper_model_size="base"):
    """Transcreve o áudio usando o Whisper e retorna os segmentos"""
    import sys

    print("🔄 Carregando o modelo Whisper...", end="", flush=True)
    model = whisper.load_model(whisper_model_size)
    print(" ✅ Modelo carregado!")

    print(f"🎵 Iniciando transcrição do arquivo: {audio_path}")
    print("⏳ Analisando áudio... (isso pode demorar alguns minutos)")

    # Usa o transcribe com verbose=True para mostrar algum progresso
    result = model.transcribe(
        audio_path,
        language="pt",  # Força português brasileiro
        word_timestamps=True,
        verbose=True
    )

    print("\n📝 Processando segmentos de transcrição...")

    # Extrai os segmentos do resultado
    segments = []
    total_segments = len(result["segments"])

    for i, segment in enumerate(result["segments"]):
        # Mostra progresso da extração de segmentos
        progress = (i + 1) / total_segments * 100
        print(f"\r📊 Extraindo segmentos: {progress:.1f}% ({i + 1}/{total_segments})", end="", flush=True)

        segments.append({
            "start": segment["start"],
            "end": segment["end"],
            "text": segment["text"],
            "words": segment.get("words", [])
        })
    
    print(f"\n🔧 Processando legendas para {len(segments)} segmentos...")

    # Processa os segmentos para criar linhas de texto para as legendas, semelhante ao instaClips.py
    for seg_idx, segment in enumerate(segments):
        # Mostra progresso do processamento de legendas
        progress = (seg_idx + 1) / len(segments) * 100
        print(f"\r📋 Processando legendas: {progress:.1f}% ({seg_idx + 1}/{len(segments)})", end="", flush=True)

        clip_words = []
        for word in segment.get("words", []):
            clip_words.append({
                "text": word["word"],
                "start": word["start"],
                "end": word["end"]
            })
        
        # Cria linhas de texto para as legendas
        width = 1080  # Largura do Instagram
        sample_text = "Sample Text for Calculation"
        font_size = 60  # Tamanho da fonte padrão

        font_path = "ARIAL.TTF"

        # Cria uma imagem temporária para medir o tamanho do texto
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()
            
        temp_img = Image.new('RGB', (1, 1))
        draw = ImageDraw.Draw(temp_img)
        
        # Calcula a largura média do caractere
        bbox = draw.textbbox((0, 0), sample_text, font=font)
        sample_width = bbox[2] - bbox[0]
        char_width = sample_width / len(sample_text)
        
        # Calcula a largura utilizável (80% da largura da tela)
        usable_width = int(width * 0.8)
        chars_per_line = int(usable_width / char_width)
        
        # Cria linhas de texto com base nas palavras
        text_lines = []
        current_line = ""
        line_start_time = None
        
        for word in clip_words:
            word_text = word["text"].strip()
            if not word_text:
                continue
                
            # Inicia uma nova linha, se necessário
            if line_start_time is None:
                line_start_time = word["start"]
            
            # Verifica se adicionar esta palavra excede o comprimento da linha
            test_line = current_line + " " + word_text if current_line else word_text
            if len(test_line) > chars_per_line:
                # Adiciona a linha atual a text_lines
                if current_line:
                    text_lines.append({
                        "text": current_line,
                        "start": line_start_time,
                        "end": word["start"]
                    })
                
                # Inicia uma nova linha com a palavra atual
                current_line = word_text
                line_start_time = word["start"]
            else:
                # Adiciona a palavra à linha atual
                current_line = test_line
        
        # Adiciona a última linha, se houver
        if current_line:
            text_lines.append({
                "text": current_line,
                "start": line_start_time,
                "end": clip_words[-1]["end"] if clip_words else segment["end"]
            })
            
        # Adiciona text_lines ao segmento
        segment["text_lines"] = text_lines
    
    print(f"\n✅ Transcrição concluída! {len(segments)} segmentos processados.")
    return segments


def parse_timestamp(timestamp):
    """Converte o timestamp 'mm:ss' para segundos"""
    parts = timestamp.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + int(seconds)
    elif len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds)
    else:
        raise ValueError(f"Formato de timestamp inválido: {timestamp}")


def review_clips(clips, transcription_segments):
    """Permite que o usuário revise e edite os clipes antes de criá-los"""
    approved_clips = []
    
    print("\n=== Clipes para Revisão ===")
    for i, clip in enumerate(clips):
        print(f"\nClipe {i+1}:")

        while True:  # Continua até que o usuário decida aprovar ou pular
            # Exibe as informações atuais do clipe
            print(f"  Tempo: {clip['start']} até {clip['end']}")
            print(f"  Motivo: {clip['reason']}")
            print(f"  Legenda: {clip['caption']}")

            # Exibe a transcrição para este período
            start_time = parse_timestamp(clip["start"])
            end_time = parse_timestamp(clip["end"])
            
            print("\n  Transcrição:")
            relevant_segments = []
            for j, segment in enumerate(transcription_segments):
                if segment["end"] >= start_time and segment["start"] <= end_time:
                    relevant_segments.append((j, segment))
            
            # Exibe os segmentos com índice para referência
            for seg_idx, (trans_idx, segment) in enumerate(relevant_segments):
                print(f"    [{seg_idx}] {segment['text']}")
            
            # Pergunta pela ação do usuário
            action = input("\nAções: [a]provar, [e]ditar transcrição, [t]rim temporizações, [s]kip, [n]ext clip: ").lower()

            if action == 'a':
                # Adiciona um buffer de um segundo ao início e ao fim
                clip = add_time_buffer(clip, buffer_seconds=1)
                approved_clips.append(clip)
                print("Clipe aprovado!")
                break
                
            elif action == 'e':
                # Edita a transcrição
                if relevant_segments:
                    seg_to_edit = input("Digite o número do segmento para editar [0, 1, ...] ou 'all' para todos os segmentos: ")

                    if seg_to_edit.lower() == 'all':
                        # Edita todos os segmentos
                        for seg_idx, (trans_idx, segment) in enumerate(relevant_segments):
                            current_text = segment['text']
                            print(f"\nEditando segmento [{seg_idx}]: {current_text}")
                            new_text = input("Digite o texto corrigido (deixe em branco para manter inalterado): ")

                            if new_text:
                                # Atualiza na transcrição
                                transcription_segments[trans_idx]['text'] = new_text
                                print(f"Segmento [{seg_idx}] atualizado")

                                # Atualiza text_lines também, se existirem
                                if 'text_lines' in transcription_segments[trans_idx]:
                                    # Cria uma representação melhor em nível de palavra
                                    words = new_text.split()
                                    seg_duration = transcription_segments[trans_idx]["end"] - transcription_segments[trans_idx]["start"]
                                    word_duration = seg_duration / len(words) if words else 0
                                    
                                    new_words = []
                                    for i, word in enumerate(words):
                                        word_start = transcription_segments[trans_idx]["start"] + (i * word_duration)
                                        word_end = word_start + word_duration
                                        new_words.append({
                                            "word": word,
                                            "start": word_start,
                                            "end": word_end
                                        })
                                    
                                    # Atualiza as palavras no segmento
                                    transcription_segments[trans_idx]['words'] = new_words

                                    # Atualiza text_lines com palavras distribuídas uniformemente
                                    lines = textwrap.wrap(new_text, width=40)  # Quebra de linha básica
                                    line_count = len(lines)
                                    line_duration = seg_duration / line_count if line_count else 0
                                    
                                    new_text_lines = []
                                    for i, line in enumerate(lines):
                                        line_start = transcription_segments[trans_idx]["start"] + (i * line_duration)
                                        line_end = line_start + line_duration
                                        new_text_lines.append({
                                            "text": line,
                                            "start": line_start,
                                            "end": line_end
                                        })

                                    transcription_segments[trans_idx]['text_lines'] = new_text_lines
                    else:
                        try:
                            seg_idx = int(seg_to_edit)
                            if 0 <= seg_idx < len(relevant_segments):
                                trans_idx, segment = relevant_segments[seg_idx]
                                current_text = segment['text']
                                print(f"Texto atual: {current_text}")
                                new_text = input("Digite o texto corrigido: ")

                                if new_text:
                                    # Atualiza na transcrição
                                    transcription_segments[trans_idx]['text'] = new_text
                                    print(f"Segmento [{seg_idx}] atualizado")

                                    # Atualiza text_lines também, se existirem
                                    if 'text_lines' in transcription_segments[trans_idx]:
                                        # Cria uma text_line simples de uma linha
                                        transcription_segments[trans_idx]['text_lines'] = [{
                                            "text": new_text,
                                            "start": transcription_segments[trans_idx]["start"],
                                            "end": transcription_segments[trans_idx]["end"]
                                        }]
                            else:
                                print("Número de segmento inválido.")
                        except ValueError:
                            print("Digite um número de segmento válido ou 'all'.")
                else:
                    print("Nenhum segmento de transcrição disponível para este clipe.")

            elif action == 't':
                new_start = input(f"Novo horário de início (atual: {clip['start']}, formato mm:ss): ")
                if new_start:
                    clip["start"] = new_start
                
                new_end = input(f"Novo horário de fim (atual: {clip['end']}, formato mm:ss): ")
                if new_end:
                    clip["end"] = new_end
                
                print(f"Horário do clipe atualizado: {clip['start']} até {clip['end']}")

            elif action == 's':
                print("Clipe pulado.")
                break
                
            elif action == 'n':
                # Adiciona um buffer de um segundo ao início e ao fim
                clip = add_time_buffer(clip, buffer_seconds=1)
                approved_clips.append(clip)
                print("Indo para o próximo clipe...")
                break
                
            else:
                print("Ação inválida. Tente novamente.")

    return approved_clips, transcription_segments


def add_time_buffer(clip, buffer_seconds=1):
    """Adiciona tempo de buffer ao início e ao fim do clipe"""
    # Analisa os horários atuais
    start_time = parse_timestamp(clip["start"])
    end_time = parse_timestamp(clip["end"])
    
    # Adiciona o buffer (subtrai do início, adiciona ao fim)
    new_start_time = max(0, start_time - buffer_seconds)
    new_end_time = end_time + buffer_seconds
    
    # Formata de volta para mm:ss
    clip["start"] = format_time(new_start_time)
    clip["end"] = format_time(new_end_time)
    
    return clip


def format_time(seconds):
    """Formata segundos no formato mm:ss"""
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"


def sanitize_filename(filename):
    """Sanitiza o nome do arquivo removendo caracteres inválidos e limitando o comprimento"""
    import re
    # Remove caracteres inválidos para nomes de arquivos
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Substitui espaços e outros caracteres problemáticos
    filename = re.sub(r'[^\w\s-]', '', filename)
    # Substitui múltiplos espaços por um único espaço e remove espaços nas extremidades
    filename = re.sub(r'\s+', ' ', filename).strip()
    # Substitui espaços por underscores
    filename = filename.replace(' ', '_')
    # Limita o comprimento para evitar problemas com o sistema de arquivos
    if len(filename) > 100:
        filename = filename[:100]
    return filename


def cv2_to_pil(cv2_img):
    """Converte imagem CV2 (BGR) para imagem PIL (RGB)"""
    return Image.fromarray(cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB))


def pil_to_cv2(pil_img):
    """Converte imagem PIL (RGB) para imagem CV2 (BGR)"""
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def draw_rounded_rectangle(draw, bbox, radius, fill):
    """Desenha um retângulo arredondado"""
    x1, y1, x2, y2 = bbox
    draw.rectangle((x1 + radius, y1, x2 - radius, y2), fill=fill)
    draw.rectangle((x1, y1 + radius, x2, y2 - radius), fill=fill)
    # Desenha os quatro cantos
    draw.pieslice((x1, y1, x1 + radius * 2, y1 + radius * 2), 180, 270, fill=fill)
    draw.pieslice((x2 - radius * 2, y1, x2, y1 + radius * 2), 270, 360, fill=fill)
    draw.pieslice((x1, y2 - radius * 2, x1 + radius * 2, y2), 90, 180, fill=fill)
    draw.pieslice((x2 - radius * 2, y2 - radius * 2, x2, y2), 0, 90, fill=fill)


def create_clip(video_path, clip, output_path, bg_color=(255, 255, 255, 230),
                highlight_color=(255, 226, 165, 220), text_color=(0, 0, 0)):
    """Cria um clipe de vídeo (sem legendas) preservando o áudio"""
    # Converte timestamps para segundos
    start_time = parse_timestamp(clip["start"])
    end_time = parse_timestamp(clip["end"])
    duration = end_time - start_time
    
    # Gera nome do arquivo com base na legenda
    if "caption" in clip and clip["caption"]:
        sanitized_caption = sanitize_filename(clip["caption"])
        base_name = sanitized_caption
    else:
        base_name = os.path.splitext(os.path.basename(output_path))[0]
    
    output_dir = os.path.dirname(output_path)
    output_path = os.path.join(output_dir, f"{base_name}.mp4")
    
    # Extrai o clipe do vídeo original com FFmpeg preservando áudio e vídeo
    # Usando -c copy para manter qualidade original e áudio
    extract_cmd = [
        "ffmpeg", "-ss", str(start_time), "-i", video_path,
        "-t", str(duration), "-c", "copy", "-avoid_negative_ts", "make_zero",
        output_path, "-y"
    ]

    print(f"Extraindo clipe: {' '.join(extract_cmd)}")
    result = subprocess.run(extract_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Erro ao extrair clipe: {result.stderr}")
        return None

    print(f"Clipe salvo em {output_path}")
    return output_path



def main():
    parser = argparse.ArgumentParser(description="Criar clipes de vídeo usando IA para encontrar momentos interessantes")
    parser.add_argument("video_path", help="Caminho para o arquivo de vídeo de entrada")
    parser.add_argument("--output-dir", default="ai_clips", help="Diretório para salvar os clipes de saída")
    parser.add_argument("--min-clips", type=int, default=3, help="Número mínimo de clipes a sugerir")
    parser.add_argument("--max-clips", type=int, default=8, help="Número máximo de clipes a sugerir")
    parser.add_argument("--whisper-model", default="base", choices=["tiny", "base", "small", "medium", "large"],
                        help="Tamanho do modelo Whisper a ser usado para transcrição")
    parser.add_argument("--api-key", help="Chave de API para o serviço LLM (opcional)")
    parser.add_argument("--no-review", action="store_true", help="Pular revisão do clipe")

    # Adiciona novos argumentos de personalização de cor
    parser.add_argument("--bg-color", default="255,255,255,230", help="Cor de fundo para legendas no formato R,G,B,A (padrão: 255,255,255,230)")
    parser.add_argument("--highlight-color", default="255,226,165,220", help="Cor de destaque para palavras ativas no formato R,G,B,A (padrão: 255,226,165,220)")
    parser.add_argument("--text-color", default="0,0,0", help="Cor do texto no formato R,G,B (padrão: 0,0,0)")

    args = parser.parse_args()
    
    # Analisa os argumentos de cor em tuplas
    bg_color = tuple(map(int, args.bg_color.split(',')))
    highlight_color = tuple(map(int, args.highlight_color.split(',')))
    text_color = tuple(map(int, args.text_color.split(',')))
    
    # Cria o diretório de saída
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    # Etapa 1: Extrair áudio do vídeo
    print("Extraindo áudio do vídeo...")
    audio_path = extract_audio(args.video_path)
    
    # Etapa 2: Transcrever áudio
    print("Transcrevendo áudio...")
    transcription_segments = transcribe_audio(audio_path, args.whisper_model)
    
    # Salva a transcrição em um arquivo
    transcription_path = os.path.join(args.output_dir, "transcription.json")
    with open(transcription_path, "w") as f:
        json.dump(transcription_segments, f, indent=2)
    
    print(f"Transcrição salva em {transcription_path}")

    # Etapa 3: Encontrar clipes interessantes usando LLM
    print("Encontrando momentos interessantes usando LLM...")
    clip_finder = LLMClipFinder(api_key=args.api_key)
    clip_suggestions = clip_finder.find_interesting_moments(
        transcription_segments, 
        min_clips=args.min_clips, 
        max_clips=args.max_clips
    )
    
    if not clip_suggestions or "clips" not in clip_suggestions or not clip_suggestions["clips"]:
        print("Nenhum clipe interessante encontrado. Saindo.")
        return
    
    clips = clip_suggestions["clips"]
    print(f"Encontrados {len(clips)} clipes potenciais")

    # Salva as sugestões de clipes em um arquivo
    suggestions_path = os.path.join(args.output_dir, "clip_suggestions.json")
    with open(suggestions_path, "w") as f:
        json.dump(clip_suggestions, f, indent=2)
    
    print(f"Sugestões de clipes salvas em {suggestions_path}")

    # Melhora os clipes com segmentos para uma melhor legendagem
    for clip in clips:
        clip_start = parse_timestamp(clip["start"])
        clip_end = parse_timestamp(clip["end"])
        
        # Encontra segmentos que se sobrepõem a este clipe
        clip["segments"] = []
        for segment in transcription_segments:
            if segment["end"] >= clip_start and segment["start"] <= clip_end:
                clip["segments"].append(segment)
    
    # Etapa 4: Revisar clipes se solicitado
    if not args.no_review:
        print("\nRevisando clipes...")
        approved_clips, updated_transcription = review_clips(clips, transcription_segments)
        
        # Salva a transcrição atualizada
        with open(transcription_path, "w") as f:
            json.dump(updated_transcription, f, indent=2)
        print(f"Transcrição atualizada salva em {transcription_path}")
    else:
        approved_clips = clips
    
    if not approved_clips:
        print("Nenhum clipe aprovado. Saindo.")
        return
    
    # Etapa 5: Criar clipes aprovados
    created_clips = []
    for i, clip in enumerate(approved_clips):
        print(f"\nCriando clipe {i+1}/{len(approved_clips)}...")

        # Gera nome do arquivo com base na legenda ou recurso de formato numerado
        if "caption" in clip and clip["caption"]:
            sanitized_caption = sanitize_filename(clip["caption"])
            filename = f"{sanitized_caption}.mp4"
        else:
            filename = f"clip_{i+1}.mp4"
            
        output_path = os.path.join(args.output_dir, filename)
        try:
            # Certifica-se de atualizar os segmentos em cada clipe com a transcrição mais recente
            if not args.no_review:
                clip_start = parse_timestamp(clip["start"])
                clip_end = parse_timestamp(clip["end"])
                clip["segments"] = []
                for segment in updated_transcription:  # Usa updated_transcription aqui
                    if segment["end"] >= clip_start and segment["start"] <= clip_end:
                        # Adiciona uma cópia profunda do segmento para evitar problemas de referência
                        import copy
                        clip["segments"].append(copy.deepcopy(segment))
                
            clip_path = create_clip(
                args.video_path, 
                clip, 
                output_path, 
                bg_color=bg_color,
                highlight_color=highlight_color,
                text_color=text_color
            )
            if clip_path:
                created_clips.append(clip_path)
                print(f"Criado com sucesso o clipe em {clip_path}")
            else:
                print(f"Falha ao criar o clipe {i+1}")
        except Exception as e:
            print(f"Erro ao criar o clipe {i+1}: {str(e)}")

    # Etapa 6: Limpar e relatar resultados
    os.remove(audio_path)
    print(f"\nProcesso concluído! Criados {len(created_clips)} clipes em {args.output_dir}")

    # Salva metadados sobre os clipes criados
    clips_metadata = {
        "created_clips": [
            {
                "path": clip_path,
                "details": approved_clips[i]
            } for i, clip_path in enumerate(created_clips)
        ]
    }
    
    metadata_path = os.path.join(args.output_dir, "clips_metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(clips_metadata, f, indent=2)

if __name__ == "__main__":
    main()
