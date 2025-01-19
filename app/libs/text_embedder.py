from typing import Union, List
from openai import OpenAI
import os


class TextEmbedder:
    """A class to convert text into embeddings using deepinfra's infrastructure."""

    def __init__(
        self,
        model: str = "BAAI/bge-m3",
        api_key: str = "lNU91OY7jk60zBlIFqJejlMkJDw6tLpM",
        base_url: str = "https://api.deepinfra.com/v1/openai"
    ):
        """
        Initialize the TextEmbedder.
        Args:
            model: The model to use for embeddings
            api_key: deepinfra API token. If None, looks for DEEPINFRA_TOKEN env variable
            base_url: The base URL for the deepinfra API
        """
        self.model = model
        self.api_key = api_key or os.getenv("DEEPINFRA_TOKEN")
        if not self.api_key:
            raise ValueError(
                "API key must be provided or set as DEEPINFRA_TOKEN environment variable")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=base_url
        )

    def get_embeddings(self, text: Union[str, List[str]]) -> List[List[float]]:
        """
        Convert text into embeddings.
        Args:
            text: Either a single string or a list of strings to convert
        Returns:
            A list of embeddings, where each embedding is a list of floats
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )

            return [data.embedding for data in response.data]

        except Exception as e:
            raise RuntimeError(f"Failed to generate embeddings: {str(e)}")
