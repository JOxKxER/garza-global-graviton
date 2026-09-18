import urllib.request
import json

def query_local_joker(prompt_text):
    url = "http://127.0.0.1:8011/v1/chat/completions"
    payload = {
        "model": "Qwen",
        "messages": [
            {"role": "system", "content": "You are Joker, a specialized local AI business partner and coding assistant built for Joel Garza's workspace."},
            {"role": "user", "content": prompt_text}
        ],
        "temperature": 0.7
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error communicating with local LLM server: {e}"

if __name__ == "__main__":
    test_prompt = "Verify mesh node status and report system readiness."
    print(f"Sending prompt to local Joker instance: '{test_prompt}'\n")
    response = query_local_joker(test_prompt)
    print(f"[Joker Response]:\n{response}")