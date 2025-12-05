#!/bin/bash

# Bash script to process pcap files in nested directory structure
# Usage: ./mpid_message_extraction.sh <input_dir> <output_dir>

# Check arguments
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <input_pcap_dir> <output_parquet_dir>"
    echo "Example: $0 /path/to/pcap/data /path/to/parquet/output"
    exit 1
fi

INPUT_DIR="$1"
OUTPUT_DIR="$2"

# Validate input directory exists
if [ ! -d "$INPUT_DIR" ]; then
    echo "Error: Input directory does not exist: $INPUT_DIR"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Get the absolute path to this script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Python script path
PYTHON_SCRIPT="$SCRIPT_DIR/mpid_message_extraction.py"

# Validate Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: Python script not found: $PYTHON_SCRIPT"
    exit 1
fi

# Track statistics
total_files=0
processed_files=0
failed_files=0

echo "============================================"
echo "MPID Message Extraction - Batch Processing"
echo "============================================"
echo "Input directory:  $INPUT_DIR"
echo "Output directory: $OUTPUT_DIR"
echo "Python script:    $PYTHON_SCRIPT"
echo "============================================"
echo ""

# Find all subdirectories in input directory
for day_dir in "$INPUT_DIR"/*; do
    # Skip if not a directory
    if [ ! -d "$day_dir" ]; then
        continue
    fi
    
    # Get the day directory name (e.g., "2025-02-03")
    day_name=$(basename "$day_dir")
    
    # Check if directory is empty
    if [ -z "$(ls -A "$day_dir"/*.pcap 2>/dev/null)" ]; then
        echo "[SKIP] Directory is empty or has no .pcap files: $day_name"
        continue
    fi
    
    # Create corresponding output subdirectory
    output_day_dir="$OUTPUT_DIR/$day_name"
    mkdir -p "$output_day_dir"
    
    echo ""
    echo "Processing directory: $day_name"
    echo "----------------------------------------"
    
    # Process each pcap file in the subdirectory
    for pcap_file in "$day_dir"/*.pcap; do
        # Skip if no pcap files match (in case of glob expansion failure)
        if [ ! -f "$pcap_file" ]; then
            continue
        fi
        
        # Get the base filename without extension
        filename=$(basename "$pcap_file" .pcap)
        
        # Construct output parquet path
        output_file="$output_day_dir/${filename}.parquet"
        
        # Increment total count
        ((total_files++))
        
        # Skip if output file already exists
        if [ -f "$output_file" ]; then
            echo "  [EXISTS] $filename.parquet (skipping)"
            ((processed_files++))
            continue
        fi
        
        echo "  [START]  $filename.pcap"
        
        # Run Python processing
        # Using python from virtual environment if available
        if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
            PYTHON_CMD="$PROJECT_ROOT/.venv/bin/python"
        else
            PYTHON_CMD="python3"
        fi
        
        # Execute the Python function
        $PYTHON_CMD -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from mpid_extraction.mpid_message_extraction import process_pcap_to_parquet

try:
    count = process_pcap_to_parquet('$pcap_file', '$output_file')
    print(f'  [DONE]   {count} messages extracted')
    sys.exit(0)
except Exception as e:
    print(f'  [ERROR]  {str(e)}')
    sys.exit(1)
"
        
        # Check exit status
        if [ $? -eq 0 ]; then
            ((processed_files++))
        else
            ((failed_files++))
            echo "  [FAILED] $filename.pcap"
        fi
    done
done

# Print summary
echo ""
echo "============================================"
echo "Processing Complete"
echo "============================================"
echo "Total files found:       $total_files"
echo "Successfully processed:  $processed_files"
echo "Failed:                  $failed_files"
echo "============================================"

# Exit with error if any files failed
if [ $failed_files -gt 0 ]; then
    exit 1
fi

exit 0
