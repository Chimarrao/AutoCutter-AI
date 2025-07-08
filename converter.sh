#!/bin/bash

mkdir -p shorts_prontos

FFPROBE=$(which ffprobe)
if [ ! -x "$FFPROBE" ]; then
  echo "Erro: ffprobe não encontrado. Instale com: sudo apt install ffmpeg"
  exit 1
fi

for f in output_folder/*_temp.mp4; do
  filename=$(basename "$f")
  name="${filename%_temp.mp4}"

  # Pega dimensões
  width=$($FFPROBE -v error -select_streams v:0 -show_entries stream=width -of default=noprint_wrappers=1:nokey=1 "$f")
  height=$($FFPROBE -v error -select_streams v:0 -show_entries stream=height -of default=noprint_wrappers=1:nokey=1 "$f")

  echo "Processando: $filename (${width}x${height})"

  if [ "$height" -ge "$width" ]; then
    echo "Vídeo vertical ou quadrado. Aplicando blur no fundo."
    ffmpeg -y -i "$f" -filter_complex "\
      [0:v]scale=1080:-1[fg]; \
      [fg]boxblur=10[bg]; \
      [bg][fg]overlay=(W-w)/2:(H-h)/2" \
      -c:a copy "shorts_prontos/${name}_9x16.mp4"
  else
    echo "Vídeo horizontal. Mantendo parte da ESQUERDA (apresentador)."
    ffmpeg -y -i "$f" -vf "\
      scale=-2:1920, \
      crop=1080:1920:0:0" \
      -c:a copy -c:v libx264 -preset fast -crf 23 \
      "shorts_prontos/${name}_9x16.mp4"
  fi

done

