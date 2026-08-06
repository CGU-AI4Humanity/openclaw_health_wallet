from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path

import timm
import torch
import torch.nn as nn
from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel
from torchvision import transforms


# ============================================================
# 1. CONFIGURATION
# ============================================================

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

AGE_MODEL_PATH = Path("retinal_age_gpu_large.pth")
HEART_MODEL_PATH = Path("best_retfound_heart_model.pth")

# ImageFolder assigns folder names alphabetically:
# heart_risk     -> 0
# no_heart_risk  -> 1
HEART_RISK_CLASS_INDEX = 0
NO_HEART_RISK_CLASS_INDEX = 1

CLASS_NAMES = {
    0: "heart_risk",
    1: "no_heart_risk",
}

MAX_FILE_SIZE_MB = 15
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/tiff",
}


# ============================================================
# 2. RETINAL AGE MODEL
# ============================================================

class RetinalAgeModel(nn.Module):
    def __init__(self, encoder: nn.Module):
        super().__init__()

        self.encoder = encoder

        self.age_head = nn.Sequential(
            nn.Linear(1024, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.encoder(x)

        # Result shape: batch_size
        return self.age_head(features).squeeze(-1)


# ============================================================
# 3. HEART-RISK MODEL
# ============================================================

class RETFoundHeartClassifier(nn.Module):
    def __init__(self, encoder: nn.Module):
        super().__init__()

        self.encoder = encoder

        self.classifier = nn.Linear(
            encoder.num_features,
            2,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.encoder(x)
        return self.classifier(features)


# ============================================================
# 4. IMAGE PREPROCESSING
# ============================================================

# RandomHorizontalFlip and ColorJitter are excluded during
# prediction because inference should remain deterministic.

inference_transform = transforms.Compose(
    [
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.5, 0.5, 0.5],
            std=[0.5, 0.5, 0.5],
        ),
    ]
)


# ============================================================
# 5. CHECKPOINT HELPERS
# ============================================================

def clean_state_dict(state_dict: dict) -> dict:
    """
    Remove prefixes sometimes introduced by DataParallel,
    DistributedDataParallel, or torch.compile.
    """

    cleaned_state_dict = {}

    for key, value in state_dict.items():
        new_key = key

        if new_key.startswith("module."):
            new_key = new_key.removeprefix("module.")

        if new_key.startswith("_orig_mod."):
            new_key = new_key.removeprefix("_orig_mod.")

        cleaned_state_dict[new_key] = value

    return cleaned_state_dict


def extract_state_dict(checkpoint: object) -> dict:
    """
    Supports checkpoints saved as:
      torch.save(model.state_dict(), path)

    It also supports:
      {"model": state_dict}
      {"state_dict": state_dict}
    """

    if not isinstance(checkpoint, dict):
        raise RuntimeError(
            "Checkpoint must contain a PyTorch state dictionary."
        )

    if "state_dict" in checkpoint:
        checkpoint = checkpoint["state_dict"]

    elif "model" in checkpoint:
        checkpoint = checkpoint["model"]

    return clean_state_dict(checkpoint)


def load_checkpoint(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"Model file not found: {path.resolve()}"
        )

    checkpoint = torch.load(
        path,
        map_location="cpu",
        weights_only=True,
    )

    return extract_state_dict(checkpoint)


# ============================================================
# 6. BUILD RETINAL AGE MODEL
# ============================================================

def build_age_model() -> RetinalAgeModel:
    encoder = timm.create_model(
        "vit_large_patch16_224",
        pretrained=False,
        num_classes=0,
        global_pool="avg",
    )

    model = RetinalAgeModel(encoder)

    state_dict = load_checkpoint(AGE_MODEL_PATH)

    missing_keys, unexpected_keys = model.load_state_dict(
        state_dict,
        strict=False,
    )

    if missing_keys or unexpected_keys:
        raise RuntimeError(
            "Retinal-age model checkpoint mismatch.\n"
            f"Missing keys: {missing_keys}\n"
            f"Unexpected keys: {unexpected_keys}"
        )

    model.to(DEVICE)
    model.eval()

    return model


# ============================================================
# 7. BUILD HEART-RISK MODEL
# ============================================================

def build_heart_model() -> RETFoundHeartClassifier:
    encoder = timm.create_model(
        "vit_large_patch16_224",
        pretrained=False,
        num_classes=0,
    )

    model = RETFoundHeartClassifier(encoder)

    state_dict = load_checkpoint(HEART_MODEL_PATH)

    missing_keys, unexpected_keys = model.load_state_dict(
        state_dict,
        strict=False,
    )

    if missing_keys or unexpected_keys:
        raise RuntimeError(
            "Heart-risk model checkpoint mismatch.\n"
            f"Missing keys: {missing_keys}\n"
            f"Unexpected keys: {unexpected_keys}"
        )

    model.to(DEVICE)
    model.eval()

    return model


# ============================================================
# 8. API RESPONSE MODELS
# ============================================================

class RetinalAgeResult(BaseModel):
    estimated_age_years: float


class HeartRiskResult(BaseModel):
    heart_risk_probability: float
    heart_risk_probability_percent: float

    no_heart_risk_probability: float
    no_heart_risk_probability_percent: float

    predicted_class_index: int
    predicted_class: str


class PredictionResponse(BaseModel):
    filename: str
    retinal_age: RetinalAgeResult
    cardiovascular_screening: HeartRiskResult
    device: str
    disclaimer: str


# ============================================================
# 9. FASTAPI STARTUP
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 60)
    print("Loading retinal prediction models")
    print("Device:", DEVICE)
    print("=" * 60)

    app.state.age_model = build_age_model()
    print("Retinal-age model loaded successfully.")

    app.state.heart_model = build_heart_model()
    print("Heart-risk model loaded successfully.")

    print("=" * 60)
    print("All models loaded.")
    print("=" * 60)

    yield

    app.state.age_model = None
    app.state.heart_model = None

    if torch.cuda.is_available():
        torch.cuda.empty_cache()


app = FastAPI(
    title="Retinal Health Prediction API",
    description=(
        "Research API for retinal-age estimation and "
        "retina-based cardiovascular-risk screening."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================
# 10. HELPER FUNCTIONS
# ============================================================

def validate_prediction(
    predicted_age: float,
    heart_risk_probability: float,
) -> None:

    if not 0 <= heart_risk_probability <= 1:
        raise RuntimeError(
            "Heart-risk probability is outside the range 0 to 1."
        )

    if predicted_age < 0 or predicted_age > 130:
        raise RuntimeError(
            "Retinal-age model returned an implausible age: "
            f"{predicted_age:.2f}"
        )


# ============================================================
# 11. API ROUTES
# ============================================================

@app.get("/")
def root():
    return {
        "application": "Retinal Health Prediction API",
        "status": "running",
        "swagger_documentation": "/docs",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "device": str(DEVICE),
        "cuda_available": torch.cuda.is_available(),
        "age_model_loaded": (
            getattr(app.state, "age_model", None) is not None
        ),
        "heart_model_loaded": (
            getattr(app.state, "heart_model", None) is not None
        ),
    }


@app.post(
    "/predict",
    response_model=PredictionResponse,
)
async def predict(
    image: UploadFile = File(...),
) -> PredictionResponse:

    # --------------------------------------------------------
    # Validate file type
    # --------------------------------------------------------

    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=(
                "Unsupported image type. "
                "Upload a JPEG, PNG, or TIFF retinal image."
            ),
        )

    # --------------------------------------------------------
    # Read uploaded image
    # --------------------------------------------------------

    image_bytes = await image.read()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="The uploaded image is empty.",
        )

    if len(image_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"The image exceeds the maximum size of "
                f"{MAX_FILE_SIZE_MB} MB."
            ),
        )

    # --------------------------------------------------------
    # Decode image
    # --------------------------------------------------------

    try:
        retinal_image = Image.open(
            BytesIO(image_bytes)
        ).convert("RGB")

        retinal_image.load()

    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid image.",
        ) from exc

    except OSError as exc:
        raise HTTPException(
            status_code=400,
            detail="The uploaded image is corrupted.",
        ) from exc

    # --------------------------------------------------------
    # Preprocess image
    # --------------------------------------------------------

    input_tensor = inference_transform(
        retinal_image
    ).unsqueeze(0).to(DEVICE)

    # --------------------------------------------------------
    # Run both models
    # --------------------------------------------------------

    try:
        with torch.inference_mode():

            # Retinal-age prediction
            age_output = app.state.age_model(
                input_tensor
            )

            # Heart-risk prediction
            heart_logits = app.state.heart_model(
                input_tensor
            )

            heart_probabilities = torch.softmax(
                heart_logits,
                dim=1,
            )

        predicted_age = float(
            age_output.reshape(-1)[0].item()
        )

        heart_risk_probability = float(
            heart_probabilities[
                0,
                HEART_RISK_CLASS_INDEX,
            ].item()
        )

        no_heart_risk_probability = float(
            heart_probabilities[
                0,
                NO_HEART_RISK_CLASS_INDEX,
            ].item()
        )

        predicted_class_index = int(
            torch.argmax(
                heart_probabilities,
                dim=1,
            ).item()
        )

        predicted_class = CLASS_NAMES[
            predicted_class_index
        ]

        validate_prediction(
            predicted_age=predicted_age,
            heart_risk_probability=heart_risk_probability,
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Model inference failed: {exc}",
        ) from exc

    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return PredictionResponse(
        filename=image.filename or "retinal-image",
        retinal_age=RetinalAgeResult(
            estimated_age_years=round(
                predicted_age,
                2,
            )
        ),
        cardiovascular_screening=HeartRiskResult(
            heart_risk_probability=round(
                heart_risk_probability,
                6,
            ),
            heart_risk_probability_percent=round(
                heart_risk_probability * 100,
                2,
            ),
            no_heart_risk_probability=round(
                no_heart_risk_probability,
                6,
            ),
            no_heart_risk_probability_percent=round(
                no_heart_risk_probability * 100,
                2,
            ),
            predicted_class_index=predicted_class_index,
            predicted_class=predicted_class,
        ),
        device=str(DEVICE),
        disclaimer=(
            "This is an experimental AI screening result. "
            "It does not diagnose heart disease and must not "
            "replace evaluation by a qualified healthcare professional."
        ),
    )

