#!/bin/bash

# Bash script to process pcap files in nested directory structure
# Usage: ./mpid_message_extraction.sh <input_dir> <output_dir> <message_types>

# Show help message
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 <input_pcap_dir> <output_parquet_dir> <message_type_codes>"
    echo ""
    echo "Arguments:"
    echo "  input_pcap_dir      Directory containing subdirectories with .pcap or .pcap.zst files"
    echo "  output_parquet_dir  Directory where output .parquet files will be saved"
    echo "  message_type_codes  ITCH message type codes to extract (space-separated)"
    echo ""
    echo "Available ITCH Message Types:"
    echo "  S - SystemEvent"
    echo "  R - StockDirectory"
    echo "  H - TradingAction"
    echo "  A - AddOrder"
    echo "  F - AddOrderMPID"
    echo "  E - Execute"
    echo "  C - ExecuteWithPrice"
    echo "  X - Cancel"
    echo "  D - Delete"
    echo "  U - Replace"
    echo "  P - Trade"
    echo "  Q - Cross"
    echo "  B - BrokenTrade"
    echo "  I - NOII"
    echo "  Y - RegSHORestriction"
    echo "  L - MarketParticipantPosition"
    echo "  V - MWCBDeclineLevel"
    echo "  W - MWCBStatus"
    echo "  K - IPOQuotingPeriod"
    echo "  J - LULDAuctionCollar"
    echo ""
    echo "Examples:"
    echo "  $0 /data/pcaps /data/output F              # Extract only AddOrderMPID"
    echo "  $0 /data/pcaps /data/output F L E          # Extract AddOrderMPID, MarketParticipantPosition, Execute"
    echo "  $0 /data/pcaps /data/output A F E C        # Extract AddOrder, AddOrderMPID, Execute, ExecuteWithPrice"
    exit 0
fi

# Check arguments
if [ "$#" -lt 3 ]; then
    echo "Error: Insufficient arguments"
    echo "Usage: $0 <input_pcap_dir> <output_parquet_dir> <message_type_codes>"
    echo "Example: $0 /path/to/pcap/data /path/to/parquet/output F L E"
    echo "Run '$0 --help' for more information"
    exit 1
fi

INPUT_DIR="$1"
OUTPUT_DIR="$2"
shift 2
MESSAGE_TYPES="$@"

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
PYTHON_SCRIPT="$SCRIPT_DIR/message_extraction.py"

# Validate Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: Python script not found: $PYTHON_SCRIPT"
    exit 1
fi

# Track statistics
total_files=0
processed_files=0
failed_files=0
total_messages_parsed=0

# Track message counts (will be built as we go)
message_counts_data=""

echo "============================================"
echo "MPID Message Extraction - Batch Processing"
echo "============================================"
echo "Input directory:  $INPUT_DIR"
echo "Output directory: $OUTPUT_DIR"
echo "Message types:    $MESSAGE_TYPES"
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
        
        # Create message type suffix (sorted for consistency)
        msg_type_suffix=$(echo "$MESSAGE_TYPES" | tr ' ' '\n' | sort | tr '\n' '-' | sed 's/-$//' | tr -d '\n')
        
        # Construct output parquet path with message types encoded in filename
        output_file="$output_day_dir/${filename}_${msg_type_suffix}.parquet"
        
        # Handle compressed files - decompress to temp location in output directory
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
            echo "  [EXISTS] ${filename}_${msg_type_suffix}.parquet (skipping)"
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
import json
sys.path.insert(0, '$PROJECT_ROOT')
from message_extraction.message_extraction import process_pcap_to_parquet

try:
    counts, total = process_pcap_to_parquet('$actual_pcap', '$output_file', '$MESSAGE_TYPES'.split())
    # Output format: counts_json|total
    print(json.dumps(counts) + '|' + str(total))
    sys.exit(0)
except Exception as e:
    print(f'ERROR: {str(e)}', file=sys.stderr)
    sys.exit(1)
" 2>&1)
        
        # Check exit status
        if [ $? -eq 0 ]; then
            # Parse the output (format: {"MessageType": count, ...}|total)
            counts_json=$(echo "$output" | tail -1 | cut -d'|' -f1)
            total=$(echo "$output" | tail -1 | cut -d'|' -f2)
            
            # Parse individual message type counts and build display string
            count_display=""
            total_extracted=0
            for msg_type in $MESSAGE_TYPES; do
                # Map ITCH code to class name
                case $msg_type in
                    S) class_name="SystemEvent" ;;
                    R) class_name="StockDirectory" ;;
                    H) class_name="TradingAction" ;;
                    A) class_name="AddOrder" ;;
                    F) class_name="AddOrderMPID" ;;
                    E) class_name="Execute" ;;
                    C) class_name="ExecuteWithPrice" ;;
                    X) class_name="Cancel" ;;
                    D) class_name="Delete" ;;
                    U) class_name="Replace" ;;
                    P) class_name="Trade" ;;
                    Q) class_name="Cross" ;;
                    B) class_name="BrokenTrade" ;;
                    I) class_name="NOII" ;;
                    Y) class_name="RegSHORestriction" ;;
                    L) class_name="MarketParticipantPosition" ;;
                    V) class_name="MWCBDeclineLevel" ;;
                    W) class_name="MWCBStatus" ;;
                    K) class_name="IPOQuotingPeriod" ;;
                    J) class_name="LULDAuctionCollar" ;;
                esac
                
                # Extract count for this message type from JSON
                count=$(echo "$counts_json" | grep -o "\"$class_name\": [0-9]*" | grep -o "[0-9]*$" || echo "0")
                
                # Add to total and build display
                ((total_extracted += count))
                
                # Update message counts data (escape newlines properly)
                if echo "$message_counts_data" | grep -q "^$msg_type:"; then
                    # Update existing count
                    old_count=$(echo "$message_counts_data" | grep "^$msg_type:" | cut -d: -f2)
                    new_count=$((old_count + count))
                    message_counts_data=$(echo "$message_counts_data" | sed "s/^$msg_type:.*/$msg_type:$new_count/")
                else
                    # Add new entry
                    if [ -n "$message_counts_data" ]; then
                        message_counts_data="${message_counts_data}
$msg_type:$count"
                    else
                        message_counts_data="$msg_type:$count"
                    fi
                fi
                
                if [ -n "$count_display" ]; then
                    count_display="$count_display, "
                fi
                count_display="${count_display}${msg_type}=$count"
            done
            
            echo "  [DONE]   Extracted: $count_display | Total messages: $total"
            ((processed_files++))
            ((total_messages_parsed += total))
        else
            ((failed_files++))
            echo "  [FAILED] $filename.pcap"
            echo "  $output"
        fi
        
        # Always clean up decompressed file if it exists
        if [ "$needs_cleanup" = true ]; then
            if [ -f "$temp_pcap" ]; then
                rm -f "$temp_pcap"
            fi
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
echo ""
echo "Messages extracted by type:"
for msg_type in $MESSAGE_TYPES; do
    # Map code to readable name for display
    case $msg_type in
        S) type_name="SystemEvent" ;;
        R) type_name="StockDirectory" ;;
        H) type_name="TradingAction" ;;
        A) type_name="AddOrder" ;;
        F) type_name="AddOrderMPID" ;;
        E) type_name="Execute" ;;
        C) type_name="ExecuteWithPrice" ;;
        X) type_name="Cancel" ;;
        D) type_name="Delete" ;;
        U) type_name="Replace" ;;
        P) type_name="Trade" ;;
        Q) type_name="Cross" ;;
        B) type_name="BrokenTrade" ;;
        I) type_name="NOII" ;;
        Y) type_name="RegSHORestriction" ;;
        L) type_name="MarketParticipantPosition" ;;
        V) type_name="MWCBDeclineLevel" ;;
        W) type_name="MWCBStatus" ;;
        K) type_name="IPOQuotingPeriod" ;;
        J) type_name="LULDAuctionCollar" ;;
    esac
    
    # Get count from message_counts_data
    count=$(echo -e "$message_counts_data" | grep "^$msg_type:" | cut -d: -f2)
    if [ -z "$count" ]; then
        count=0
    fi
    
    echo "  $msg_type ($type_name): $count"
done
echo ""
echo "Total messages parsed:   $total_messages_parsed"
echo "============================================"

# Exit with error if any files failed
if [ $failed_files -gt 0 ]; then
    exit 1
fi

exit 0
