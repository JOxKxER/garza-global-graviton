Start-Process powershell -ArgumentList "-NoExit", "-Command", "llama serve --model 'C:\Users\JOXKX\.cache\huggingface\hub\models--ggml-org--Qwen2.5-Coder-3B-Instruct-Q8_0-GGUF\snapshots\4944a3e9ecbaacda76873e9577d038400413772c\qwen2.5-coder-3b-instruct-q8_0.gguf' --device none -ub 1024 -b 1024 --ctx-size 0 --cache-reuse 256 -np 2 --port 8011"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "llama serve -hf ggml-org/Nomic-Embed-Text-V2-GGUF --device none -ub 2048 -b 2048 --ctx-size 2048 --embeddings --port 8010"
Write-Output "Local AI servers are starting up..."
