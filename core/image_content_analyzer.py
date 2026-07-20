#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: image_content_analyzer.py
# Purpose: AI-based image content analysis using CLIP
#
# Description:
# Uses OpenAI's CLIP model to automatically identify content in images.
# Can detect objects, scenes, people, locations, and more based on
# text descriptions. All processing is done locally (privacy-safe).
#
# Categories detected:
# - Military equipment, personnel, vehicles
# - Vehicles (trucks, motorcycles, cars, aircraft)
# - Terrain/landscapes (desert, urban, forest, mountains, beach)
# - Regions (Middle East/Iraq, Texas, Ohio)
# - People & groups
# - Events & activities
# - Indoor/outdoor, time of day
#
# Author: Tim Canady
# Created: 2025-11-15
#
# Version: 1.0.0
# Last Modified: 2025-11-15 by Tim Canady
#
# Revision History:
# - 1.0.0 (2025-11-15): Initial AI content analyzer with CLIP — Tim Canady
###################################################################

from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging
import yaml

logger = logging.getLogger(__name__)

# Check for required libraries
try:
    from PIL import Image
    PIL_AVAILABLE = True

    # Register HEIC support if available
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
        logger.debug("HEIC support enabled")
    except ImportError:
        logger.debug("HEIC support not available (install pillow-heif for .heic files)")
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL/Pillow not available")

try:
    import torch
    from transformers import CLIPProcessor, CLIPModel
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False
    logger.warning("CLIP not available. Install with: pip install torch transformers")


class ImageContentAnalyzer:
    """
    AI-based image content analyzer using CLIP.

    Automatically identifies content in images (objects, scenes, people, etc.)
    based on text descriptions. All processing is local (privacy-safe).
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the image content analyzer.

        Args:
            config_path: Path to categories configuration YAML file
        """
        if not PIL_AVAILABLE:
            raise ImportError("PIL/Pillow required for image analysis")

        if not CLIP_AVAILABLE:
            raise ImportError(
                "CLIP model not available. Install with:\n"
                "  pip install torch transformers\n"
                "  or\n"
                "  pip install torch torchvision transformers"
            )

        # Load configuration
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "image_ai_categories.yaml"

        self.config = self._load_config(config_path)
        self.confidence_threshold = self.config.get('confidence_threshold', 0.25)

        # Initialize CLIP model (lazy loading)
        self.model = None
        self.processor = None
        self._model_loaded = False

        logger.info("ImageContentAnalyzer initialized")

    def _load_config(self, config_path: Path) -> dict:
        """Load categories configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded AI categories from {config_path}")
                return config
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            # Return minimal config
            return {
                'confidence_threshold': 0.25,
                'categories': {}
            }

    def _load_model(self):
        """Load CLIP model (lazy loading on first use)."""
        if self._model_loaded:
            return

        try:
            logger.info("Loading CLIP model (this may take a moment on first run)...")

            # Use smaller, faster model by default
            model_name = "openai/clip-vit-base-patch32"

            # Use safetensors format (safer and required for older torch versions)
            # Try local files first, fall back to download if needed
            try:
                self.model = CLIPModel.from_pretrained(
                    model_name,
                    use_safetensors=True,
                    local_files_only=True  # Use cached files to avoid network issues
                )
                self.processor = CLIPProcessor.from_pretrained(
                    model_name,
                    local_files_only=True
                )
            except Exception as e:
                logger.info(f"Local files not found, downloading: {e}")
                self.model = CLIPModel.from_pretrained(
                    model_name,
                    use_safetensors=True,
                    local_files_only=False
                )
                self.processor = CLIPProcessor.from_pretrained(
                    model_name,
                    local_files_only=False
                )

            # Move to GPU if available
            if torch.cuda.is_available():
                self.model = self.model.to('cuda')
                logger.info("✅ CLIP model loaded on GPU")
            else:
                logger.info("✅ CLIP model loaded on CPU (GPU recommended for speed)")

            self._model_loaded = True

        except Exception as e:
            logger.error(f"Error loading CLIP model: {e}")
            raise

    def analyze(self, image_path: Path) -> List[str]:
        """
        Analyze image content and return identified keywords.

        Args:
            image_path: Path to image file

        Returns:
            List of keywords identified in the image
        """
        # Load model on first use
        if not self._model_loaded:
            self._load_model()

        try:
            # Open image
            image = Image.open(image_path).convert('RGB')

            # Get all enabled categories and their descriptions
            all_descriptions = []
            description_to_keywords = {}  # Map description to keywords

            categories = self.config.get('categories', {})
            for category_name, category_config in categories.items():
                if not category_config.get('enabled', False):
                    continue

                descriptions = category_config.get('descriptions', [])
                keywords = category_config.get('keywords', [])

                for desc in descriptions:
                    all_descriptions.append(desc)
                    description_to_keywords[desc] = keywords

            if not all_descriptions:
                logger.warning("No enabled categories found in config")
                return []

            # Process with CLIP
            inputs = self.processor(
                text=all_descriptions,
                images=image,
                return_tensors="pt",
                padding=True
            )

            # Move to GPU if available
            if torch.cuda.is_available():
                inputs = {k: v.to('cuda') for k, v in inputs.items()}

            # Get predictions
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1).cpu().numpy()[0]

            # Collect keywords for descriptions that exceed threshold
            identified_keywords = set()
            matches = []

            for i, (desc, prob) in enumerate(zip(all_descriptions, probs)):
                if prob >= self.confidence_threshold:
                    keywords = description_to_keywords.get(desc, [])
                    identified_keywords.update(keywords)
                    matches.append((desc, prob))

            # Log matches for debugging
            if matches:
                logger.debug(f"Matches for {image_path.name}:")
                for desc, prob in sorted(matches, key=lambda x: x[1], reverse=True)[:5]:
                    logger.debug(f"  {desc}: {prob:.2%}")

            return sorted(list(identified_keywords))

        except Exception as e:
            logger.error(f"Error analyzing {image_path}: {e}")
            return []

    def analyze_with_scores(self, image_path: Path) -> List[Tuple[str, float]]:
        """
        Analyze image and return keywords with confidence scores.

        Args:
            image_path: Path to image file

        Returns:
            List of (keyword, confidence) tuples, sorted by confidence
        """
        # Load model on first use
        if not self._model_loaded:
            self._load_model()

        try:
            # Open image
            image = Image.open(image_path).convert('RGB')

            # Get all enabled categories and their descriptions
            all_descriptions = []
            description_to_keywords = {}

            categories = self.config.get('categories', {})
            for category_name, category_config in categories.items():
                if not category_config.get('enabled', False):
                    continue

                descriptions = category_config.get('descriptions', [])
                keywords = category_config.get('keywords', [])

                for desc in descriptions:
                    all_descriptions.append(desc)
                    description_to_keywords[desc] = keywords

            if not all_descriptions:
                return []

            # Process with CLIP
            inputs = self.processor(
                text=all_descriptions,
                images=image,
                return_tensors="pt",
                padding=True
            )

            # Move to GPU if available
            if torch.cuda.is_available():
                inputs = {k: v.to('cuda') for k, v in inputs.items()}

            # Get predictions
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1).cpu().numpy()[0]

            # Collect keywords with max confidence score
            keyword_scores = {}

            for i, (desc, prob) in enumerate(zip(all_descriptions, probs)):
                if prob >= self.confidence_threshold:
                    keywords = description_to_keywords.get(desc, [])
                    for keyword in keywords:
                        # Keep max score if keyword appears in multiple categories
                        if keyword not in keyword_scores or prob > keyword_scores[keyword]:
                            keyword_scores[keyword] = prob

            # Return sorted by confidence
            return sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True)

        except Exception as e:
            logger.error(f"Error analyzing {image_path}: {e}")
            return []

    def get_enabled_categories(self) -> List[str]:
        """Get list of enabled category names."""
        categories = self.config.get('categories', {})
        return [
            name for name, config in categories.items()
            if config.get('enabled', False)
        ]

    def get_all_keywords(self) -> List[str]:
        """Get list of all possible keywords from enabled categories."""
        keywords = set()
        categories = self.config.get('categories', {})

        for category_config in categories.values():
            if category_config.get('enabled', False):
                keywords.update(category_config.get('keywords', []))

        return sorted(list(keywords))

    @staticmethod
    def is_available() -> bool:
        """Check if CLIP is available for use."""
        return PIL_AVAILABLE and CLIP_AVAILABLE


def check_requirements():
    """Check if all required libraries are installed."""
    missing = []

    if not PIL_AVAILABLE:
        missing.append("Pillow")

    if not CLIP_AVAILABLE:
        missing.append("torch and transformers")

    if missing:
        print("❌ Missing required libraries:")
        for lib in missing:
            print(f"   - {lib}")
        print("\n📦 Install with:")
        print("   pip install Pillow torch transformers")
        print("   or")
        print("   pip install Pillow torch torchvision transformers")
        return False

    print("✅ All required libraries are installed")
    return True


if __name__ == "__main__":
    # Quick test
    import sys

    if not check_requirements():
        sys.exit(1)

    if len(sys.argv) > 1:
        # Test specific image
        image_path = Path(sys.argv[1])
        if image_path.exists():
            print(f"\n🔍 Analyzing: {image_path}")

            analyzer = ImageContentAnalyzer()

            # Show all scores for debugging
            keywords_with_scores = analyzer.analyze_with_scores(image_path)

            if keywords_with_scores:
                print("\n✅ Identified content (above threshold):")
                for keyword, score in keywords_with_scores:
                    print(f"   {keyword}: {score:.2%} confidence")
            else:
                print(f"\n⚠️  No content identified above threshold ({analyzer.confidence_threshold:.2%})")

                # Show top 10 scores even if below threshold for debugging
                print("\n📊 Top detected categories (all scores):")
                try:
                    # Re-analyze to get all scores
                    image = Image.open(image_path).convert('RGB')
                    all_descriptions = []
                    description_to_keywords = {}

                    categories = analyzer.config.get('categories', {})
                    for category_name, category_config in categories.items():
                        if not category_config.get('enabled', False):
                            continue
                        descriptions = category_config.get('descriptions', [])
                        keywords = category_config.get('keywords', [])
                        for desc in descriptions:
                            all_descriptions.append(desc)
                            description_to_keywords[desc] = keywords

                    if all_descriptions:
                        inputs = analyzer.processor(
                            text=all_descriptions,
                            images=image,
                            return_tensors="pt",
                            padding=True
                        )

                        with torch.no_grad():
                            outputs = analyzer.model(**inputs)
                            logits_per_image = outputs.logits_per_image
                            probs = logits_per_image.softmax(dim=1).cpu().numpy()[0]

                        # Get top scores
                        top_indices = probs.argsort()[-10:][::-1]
                        for idx in top_indices:
                            desc = all_descriptions[idx]
                            prob = probs[idx]
                            keywords = description_to_keywords.get(desc, [])
                            keyword_str = ', '.join(keywords) if keywords else desc
                            print(f"   {keyword_str}: {prob:.2%} (from: {desc})")
                except Exception as e:
                    print(f"   Error showing debug info: {e}")

        else:
            print(f"❌ File not found: {image_path}")
    else:
        print("Usage: python image_content_analyzer.py /path/to/image.jpg")
        print("\nThis will analyze the image and show identified content.")
