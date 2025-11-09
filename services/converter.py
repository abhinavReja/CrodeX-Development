# filepath: services/converter.py

from typing import Dict, List, Callable
from services.gemini_api import GeminiService  # Changed from claude_api
from services.analyzer import FrameworkAnalyzer
import json
import logging

logger = logging.getLogger(__name__)


class ProjectConverter:
    """
    Orchestrates the entire conversion process
    Coordinates between analyzer and Gemini API
    """
    
    def __init__(self, gemini_api_key: str = None):
        """Initialize with Gemini API"""
        self.gemini = GeminiService(gemini_api_key)
        self.analyzer = FrameworkAnalyzer()
        logger.info("✅ ProjectConverter initialized with Gemini API")
    
    def full_conversion_pipeline(
        self,
        files: Dict[str, str],
        target_framework: str,
        project_context: Dict,
        progress_callback: Callable = None
    ) -> Dict:
        """
        Complete conversion pipeline using Gemini
        """
        try:
            logger.info("Starting conversion pipeline")
            
            # Step 1: Initial Analysis
            if progress_callback:
                progress_callback('analysis', 'Analyzing project structure...')
            
            initial_analysis = self.analyzer.analyze_structure(files)
            logger.info(f"Initial analysis: {len(files)} files")
            
            # Step 2: Gemini Deep Analysis
            if progress_callback:
                progress_callback('analysis', 'AI analyzing with Gemini...')
            
            gemini_analysis = self.gemini.analyze_project_structure(files)
            source_framework = gemini_analysis.get('framework', 'unknown')
            logger.info(f"Detected framework: {source_framework}")
            
            # Step 3: Convert Files
            if progress_callback:
                progress_callback('conversion', 'Converting files with Gemini AI...')
            
            def conversion_progress(current, total, filename):
                if progress_callback:
                    progress_callback(
                        'conversion',
                        f'Converting {current}/{total}: {filename}'
                    )
            
            converted_files = self.gemini.batch_convert_files(
                files=files,
                source_framework=source_framework,
                target_framework=target_framework,
                project_context=project_context,
                progress_callback=conversion_progress
            )
            
            logger.info(f"Converted {len(converted_files)} files")
            
            # Step 4: Generate Migration Guide
            if progress_callback:
                progress_callback('documentation', 'Generating migration guide...')
            
            migration_guide = self.gemini.generate_migration_guide(
                source_framework=source_framework,
                target_framework=target_framework,
                converted_files=converted_files,
                project_context=project_context
            )
            
            # Step 5: Create Summary
            summary = self._create_conversion_summary(
                source_framework=source_framework,
                target_framework=target_framework,
                initial_analysis=initial_analysis,
                gemini_analysis=gemini_analysis,
                converted_files=converted_files
            )
            
            logger.info("✅ Conversion pipeline complete")
            
            return {
                'status': 'success',
                'source_framework': source_framework,
                'target_framework': target_framework,
                'analysis': {
                    'initial': initial_analysis,
                    'gemini': gemini_analysis
                },
                'converted_files': converted_files,
                'migration_guide': migration_guide,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"❌ Conversion pipeline failed: {str(e)}")
            raise
    
    def _create_conversion_summary(
        self,
        source_framework: str,
        target_framework: str,
        initial_analysis: Dict,
        gemini_analysis: Dict,
        converted_files: List[Dict]
    ) -> Dict:
        """Create conversion summary report"""
        
        total_files = len(converted_files)
        successful = len([f for f in converted_files if not f.get('error')])
        failed = total_files - successful
        warnings = sum(len(f.get('warnings', [])) for f in converted_files)
        
        return {
            'conversion_stats': {
                'total_files_converted': total_files,
                'successful_conversions': successful,
                'failed_conversions': failed,
                'total_warnings': warnings,
                'source_framework': source_framework,
                'target_framework': target_framework,
                'confidence_score': gemini_analysis.get('confidence', 0)
            },
            'file_breakdown': {
                'controllers': len([f for f in converted_files if 'controller' in f.get('original_path', '').lower()]),
                'models': len([f for f in converted_files if 'model' in f.get('original_path', '').lower()]),
                'views': len([f for f in converted_files if 'view' in f.get('original_path', '').lower()]),
                'other': len([f for f in converted_files if not any(
                    t in f.get('original_path', '').lower() 
                    for t in ['controller', 'model', 'view']
                )])
            },
            'warnings': [
                {
                    'file': f.get('original_path', 'unknown'),
                    'warnings': f.get('warnings', [])
                }
                for f in converted_files if f.get('warnings')
            ],
            'errors': [
                {
                    'file': f.get('original_path', 'unknown'),
                    'error': f.get('error')
                }
                for f in converted_files if f.get('error')
            ]
        }