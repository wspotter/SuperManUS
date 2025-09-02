import unittest
import asyncio
from prediction_module import app, log_interaction
from fastapi.testclient import TestClient
import time

client = TestClient(app)

class TestPredictionModule(unittest.TestCase):
    def setUp(self):
        self.session_id = "test_123"
        asyncio.run(log_interaction(self.session_id, "create_image", {"prompt": "test"}))

    def test_prediction_endpoint(self):
        start = time.time()
        response = client.post("/predict", json={"session_id": self.session_id})
        self.assertEqual(response.status_code, 200)
        self.assertIn("predicted_intents", response.json())
        self.assertLess(time.time() - start, 0.1)  # Ensure <100ms

    def test_disabled_prediction(self):
        global ENABLE_PREDICTION
        ENABLE_PREDICTION = False
        response = client.post("/register")
        self.assertEqual(response.json()["status"], "disabled")

if __name__ == "__main__":
    unittest.main()