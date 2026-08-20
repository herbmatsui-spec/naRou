#!/usr/bin/env python3
"""
Gemini Asset Generator for naRou
Handles batch generation of game assets using Google's Gemini AI.
"""

import os
import yaml
import argparse
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

# Try to import google.generativeai, handle gracefully if not available
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("Google Generative AI not available. Install with: pip install google-generativeai")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiAssetGenerator:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini Asset Generator.
        
        Args:
            api_key: Google AI API key (if None, will try to get from environment)
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.workspace_root = Path("assets/gemini_workspace")
        self.prompt_templates = self.load_prompt_templates()
        
        if GEMINI_AVAILABLE and self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro-vision')
            logger.info("Gemini Asset Generator initialized with API key")
        elif GEMINI_AVAILABLE:
            logger.warning("Gemini API key not found. Set GEMINI_API_KEY environment variable.")
        else:
            logger.warning("Google Generative AI library not available")
    
    def load_prompt_templates(self) -> Dict[str, Any]:
        """Load prompt templates from YAML file."""
        template_path = Path("tools/gemini_prompt_templates.yaml")
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        else:
            logger.warning(f"Prompt templates file not found: {template_path}")
            return {}
    
    def generate_asset(self, category: str, prompt_params: Dict[str, str], 
                      output_dir: Optional[Path] = None, 
                      variant_id: int = 0) -> Optional[Path]:
        """
        Generate a single asset using Gemini.
        
        Args:
            category: Asset category (terrain, entity, effect, ui, etc.)
            prompt_params: Parameters to fill in the prompt template
            output_dir: Directory to save the asset (defaults to category workspace)
            variant_id: Variant identifier for the asset
            
        Returns:
            Path to generated asset if successful, None otherwise
        """
        if not GEMINI_AVAILABLE or not self.api_key:
            logger.error("Cannot generate asset: Gemini API not available or no API key")
            return None
            
        if category not in self.prompt_templates.get('categories', {}):
            logger.error(f"Unknown category: {category}")
            return None
            
        # Get the base prompt for this category
        category_info = self.prompt_templates['categories'][category]
        base_prompt = category_info['base_prompt']
        
        # Fill in the prompt with parameters
        try:
            prompt = base_prompt.format(**prompt_params)
        except KeyError as e:
            logger.error(f"Missing parameter for prompt: {e}")
            return None
            
        # Add negative prompt if specified
        negative_prompt = category_info.get('negative', '')
        if negative_prompt:
            prompt += f"\n\nNegative prompt: {negative_prompt}"
            
        # Determine output directory
        if output_dir is None:
            output_dir = self.workspace_root / category
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        param_str = "_".join([f"{k}{v}" for k, v in sorted(prompt_params.items())])
        filename = f"{category}_{param_str}_v{variant_id}.png"
        output_path = output_dir / filename
        
        # TODO: Actual Gemini image generation would go here
        # This is a placeholder since we can't actually call the API without keys
        logger.info(f"Would generate asset: {prompt}")
        logger.info(f"Would save to: {output_path}")
        
        # Create a placeholder file for now
        placeholder_path = output_dir / f"placeholder_{filename}"
        placeholder_path.write_text(f"# Placeholder for Gemini-generated asset\n")
        logger.info(f"Created placeholder: {placeholder_path}")
        
        return output_path
    
    def batch_generate(self, category: str, param_combinations: List[Dict[str, str]], 
                      variants_per_combo: int = 1) -> List[Path]:
        """
        Generate multiple assets in batch.
        
        Args:
            category: Asset category
            param_combinations: List of parameter dictionaries
            variants_per_combo: Number of variants to generate per parameter combination
            
        Returns:
            List of paths to generated assets
        """
        generated_assets = []
        
        for i, params in enumerate(param_combinations):
            logger.info(f"Generating combination {i+1}/{len(param_combinations)}: {params}")
            
            for variant in range(variants_per_combo):
                asset_path = self.generate_asset(category, params, variant_id=variant)
                if asset_path:
                    generated_assets.append(asset_path)
                    
                # Rate limiting to avoid API limits
                time.sleep(0.5)
                
        return generated_assets

def main():
    parser = argparse.ArgumentParser(description='Generate assets using Gemini AI')
    parser.add_argument('--category', required=True, 
                       choices=['terrain', 'entity', 'object', 'effect', 'ui', 'background', 'portrait'],
                       help='Asset category to generate')
    parser.add_argument('--count', type=int, default=1,
                       help='Number of assets to generate (for simple mode)')
    parser.add_argument('--all-combos', action='store_true',
                       help='Generate all combinations from prompt templates')
    parser.add_argument('--variants', type=int, default=1,
                       help='Number of variants per combination')
    parser.add_argument('--biome', help='Biome parameter')
    parser.add_argument('--time_of_day', help='Time of day parameter')
    parser.add_argument('--palette', help='Palette parameter')
    parser.add_argument('--pose', help='Pose parameter')
    parser.add_argument('--equipment', help='Equipment parameter')
    parser.add_argument('--expression', help='Expression parameter')
    parser.add_argument('--lighting', help='Lighting parameter')
    parser.add_argument('--component_type', help='Component type parameter')
    parser.add_argument('--theme', help='Theme parameter')
    parser.add_argument('--element', help='Element parameter')
    parser.add_argument('--effect_type', help='Effect type parameter')
    parser.add_argument('--frame_count', help='Frame count parameter')
    parser.add_argument('--layer_count', help='Layer count parameter')
    parser.add_argument('--weather', help='Weather parameter')
    parser.add_argument('--race', help='Race parameter')
    parser.add_argument('--class_type', dest='class_type', help='Class parameter')
    parser.add_argument('--gender', help='Gender parameter')
    
    args = parser.parse_args()
    
    generator = GeminiAssetGenerator()
    
    if args.all_combos:
        # Generate all combinations from the prompt template
        if args.category not in generator.prompt_templates.get('categories', {}):
            logger.error(f"Unknown category: {args.category}")
            return 1
            
        category_info = generator.prompt_templates['categories'][args.category]
        params_info = category_info.get('params', {})
        
        # Generate all combinations of parameters
        import itertools
        param_names = list(params_info.keys())
        param_values = [params_info[name] for name in param_names]
        
        param_combinations = []
        for combination in itertools.product(*param_values):
            param_dict = dict(zip(param_names, combination))
            param_combinations.append(param_dict)
            
        logger.info(f"Generating {len(param_combinations)} parameter combinations "
                   f"with {args.variants} variants each ({len(param_combinations) * args.variants} total assets)")
                   
        generated = generator.batch_generate(args.category, param_combinations, args.variants)
        logger.info(f"Generated {len(generated)} assets")
        
    else:
        # Simple mode: generate specified count with given parameters
        prompt_params = {}
        if args.biome:
            prompt_params['biome'] = args.biome
        if args.time_of_day:
            prompt_params['time_of_day'] = args.time_of_day
        if args.palette:
            prompt_params['palette'] = args.palette
        if args.pose:
            prompt_params['pose'] = args.pose
        if args.equipment:
            prompt_params['equipment'] = args.equipment
        if args.expression:
            prompt_params['expression'] = args.expression
        if args.lighting:
            prompt_params['lighting'] = args.lighting
        if args.component_type:
            prompt_params['component_type'] = args.component_type
        if args.theme:
            prompt_params['theme'] = args.theme
        if args.element:
            prompt_params['element'] = args.element
        if args.effect_type:
            prompt_params['effect_type'] = args.effect_type
        if args.frame_count:
            prompt_params['frame_count'] = args.frame_count
        if args.layer_count:
            prompt_params['layer_count'] = args.layer_count
        if args.weather:
            prompt_params['weather'] = args.weather
        if args.race:
            prompt_params['race'] = args.race
        if args.class_type:
            prompt_params['class'] = args.class_type
        if args.gender:
            prompt_params['gender'] = args.gender
            
        logger.info(f"Generating {args.count} assets with parameters: {prompt_params}")
        
        generated = []
        for i in range(args.count):
            asset_path = generator.generate_asset(args.category, prompt_params, variant_id=i)
            if asset_path:
                generated.append(asset_path)
                
        logger.info(f"Generated {len(generated)} assets")
    
    return 0

if __name__ == '__main__':
    exit(main())