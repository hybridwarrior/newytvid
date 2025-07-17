#!/usr/bin/env python3
"""
Test script to manually trigger the pipeline processing
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from scripts.pipeline_processor_integrated import PipelineProcessorIntegrated

def test_pipeline_processing():
    """Test the integrated pipeline processing"""
    
    # Create a test trigger file
    test_trigger = {
        'file_id': 'test_' + datetime.now().strftime('%Y%m%d_%H%M%S'),
        'filename': '0714 (1).mov',
        'path': '/opt/clipper/data/input/0714 (1).mov',
        'size': 100000000,
        'modified': datetime.now().isoformat(),
        'triggered_at': datetime.now().isoformat(),
        'source': 'manual_test'
    }
    
    print("🧪 Testing integrated pipeline processing...")
    print(f"Test trigger data: {json.dumps(test_trigger, indent=2)}")
    
    try:
        # Initialize the processor
        config = Config()
        processor = PipelineProcessorIntegrated(config)
        
        # Process the test file
        processor.process_file(test_trigger)
        
        print("✅ Pipeline processing completed successfully!")
        
    except Exception as e:
        print(f"❌ Pipeline processing failed: {e}")
        raise

if __name__ == "__main__":
    test_pipeline_processing()