import requests
import json

NLP_API_URL = "http://127.0.0.1:8000/nlp/nlp/query"

USER_UUID = "4841d633-34a4-4ba8-90d2-d3b72090b5f6"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImdyZUBlamVtcGxvLmNvbSIsImVtYWlsIjoiZ3JlQGVqZW1wbG8uY29tIiwicHJvZmlsZUlkIjoiOTFjNTZkMTktODYwZC00YjJkLWIwMTEtYTVkNDlkYTkzNjY3Iiwicm9sZUlkIjoiM2UwOGEwODgtYjI1Yy00YzJkLWE0ZGItOWQ1OTk0M2Q1NzlmIiwiaWF0IjoxNzYwNjQxMTAxLCJleHAiOjE3NjA2NDIwMDF9.--R1JmbK_z3SFDWqoJG87QsDKSkmdGmt2akHaBd4xqM"
def send_nlp_query(prompt: str, user_id: str = USER_UUID, auth_token: str = AUTH_TOKEN):
    """
    Sends a query to the NLP API and returns the response.
    """
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {auth_token}"}
    payload = {"prompt": prompt, "userId": user_id}
    try:
        response = requests.post(NLP_API_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status() 
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"Error HTTP al conectar con la API NLP: {e}")
        if response.text:
            print(f"Detalle del error: {response.text}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con la API NLP: {e}")
        return None

def chat_interface():
    """
    Provides a simple command-line chat interface.
    """
    print("¡Bienvenido al Chatbot de IA! Escribe 'salir' para terminar la conversación.")
    print(f"Usuario actual: {USER_UUID}")
    print("-" * 60)
    
    while True:
        user_input = input("\nTú: ").strip()
        
        if not user_input:
            print("Por favor, escribe algo.")
            continue
            
        if user_input.lower() in ['salir', 'exit', 'quit']:
            print("¡Hasta luego!")
            break

        response_data = send_nlp_query(user_input, user_id=USER_UUID, auth_token=AUTH_TOKEN)
        if response_data:
            ai_response = response_data.get('response', 'No response from AI.')
            user_name = response_data.get('user_name', '')
            
            print(f"\nIA: {ai_response}")
            
            if user_name:
                print(f"[Usuario: {user_name}]")
        else:
            print("\nIA: No pude obtener una respuesta en este momento. Por favor, intenta de nuevo.")

if __name__ == "__main__":
    chat_interface()