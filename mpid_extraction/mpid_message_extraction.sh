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
total_messages_extracted=0
total_messages_parsed=0

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
    if [ -z "$(ls -A "$day_dir"/*.pcap "$day_dir"/*.pcap.zst 2>/dev/null)" ]; then
        echo ""
        echo "[SKIP] Directory is empty or has no .pcap/.pcap.zst files: $day_name"
        continue
    fi
    
    # Create corresponding output subdirectory
    output_day_dir="$OUTPUT_DIR/$day_name"
    mkdir -p "$output_day_dir"
    
    echo ""
    echo "Processing directory: $day_name"
    echo "----------------------------------------"
    
    # Process each pcap file in the subdirectory (including compressed)
    for pcap_file in "$day_dir"/*.pcap "$day_dir"/*.pcap.zst; do
        # Skip if no pcap files match (in case of glob expansion failure)
        if [ ! -f "$pcap_file" ]; then
            continue
        fi
        
        # Get the base filename without extension(s)
        filename=$(basename "$pcap_file")
        filename="${filename%.pcap.zst}"
        filename="${filename%.pcap}"
        
        # Construct output parquet path
        output_file="$output_day_dir/${filename}.parquet"
        
        # Handle compressed files - decompress to temp location
        if [[ "$pcap_file" == *.zst ]]; then
            temp_pcap="$output_day_dir/.temp_${filename}.pcap"
            actual_pcap="$temp_pcap"
            needs_cleanup=true
        else
            actual_pcap="$pcap_file"
            needs_cleanup=false
        fi
        
        # Increment total count
        ((total_files++))
        
        # Skip if output file already exists
        if [ -f "$output_file" ]; then
            echo "  [EXISTS] $filename.parquet (skipping)"
            ((processed_files++))
            continue
        fi
        
        # Decompress if needed
        if [ "$needs_cleanup" = true ]; then
            echo "  [DECOMP] $filename.pcap.zst"
            unzstd -d "$pcap_file" -o "$temp_pcap" --quiet
            if [ $? -ne 0 ]; then
                echo "  [ERROR]  Failed to decompress"
                ((failed_files++))
                continue
            fi
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
        output=$($PYTHON_CMD -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from mpid_extraction.mpid_message_extraction import process_pcap_to_parquet

try:
    extracted, total = process_pcap_to_parquet('$actual_pcap', '$output_file')
    print(f'{extracted},{total}')
    sys.exit(0)
except Exception as e:
    print(f'ERROR: {str(e)}', file=sys.stderr)
    sys.exit(1)
" 2>&1)
        
        # Check exit status
        if [ $? -eq 0 ]; then
            # Parse the output
            extracted=$(echo "$output" | tail -1 | cut -d',' -f1)
            total=$(echo "$output" | tail -1 | cut -d',' -f2)
            
            echo "  [DONE]   $extracted messages extracted, $total messages total"
            ((processed_files++))
            ((total_messages_extracted += extracted))
            ((total_messages_parsed += total))
        else
            ((failed_files++))
            echo "  [FAILED] $filename.pcap"
            echo "  $output"
        fi
        
        # Clean up decompressed file if needed
        if [ "$needs_cleanup" = true ] && [ -f "$temp_pcap" ]; then
            rm -f "$temp_pcap"
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
echo "Messages extracted:      $total_messages_extracted"
echo "Total messages parsed:   $total_messages_parsed"
echo "============================================"

# Exit with error if any files failed
if [ $failed_files -gt 0 ]; then
    exit 1
fi

exit 0
