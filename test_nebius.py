from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()

client = OpenAI(
    base_url=os.getenv("NEBIUS_BASE_URL"),
    api_key=os.getenv("NEBIUS_API_KEY")
)

models = client.models.list()

print("\nAvailable models:\n")

for model in models.data:
    print(model.id)