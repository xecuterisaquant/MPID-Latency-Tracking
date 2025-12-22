"""
Preprocess NASDAQ files: Combine 58 small files into 1 filtered file per day
This is a ONE-TIME step to prepare data for fast matching
"""
import pandas as pd
from pathlib import Path
import logging
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import ALL_DATES

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def preprocess_day(nasdaq_dir: Path, date_str: str):
    """Combine and filter NASDAQ files for one day - MEMORY SAFE"""
    # Try both extracted_md and extracted (different days have different folder names)
    date_folder = nasdaq_dir / date_str / "extracted_md" / date_str
    if not date_folder.exists():
        date_folder = nasdaq_dir / date_str / "extracted" / date_str
    
    if not date_folder.exists():
        logger.warning(f"Folder not found: {date_folder}")
        return
    
    parquet_files = list(date_folder.glob("*.parquet"))
    logger.info(f"Processing {date_str}: {len(parquet_files)} files")
    
    # Process ONE file at a time, write to temp files
    temp_dir = nasdaq_dir / "temp"
    temp_dir.mkdir(exist_ok=True)
    
    temp_files = []
    
    for i, file in enumerate(parquet_files, 1):
        try:
            logger.info(f"  [{i}/{len(parquet_files)}] {file.name}")
            
            # Load only this file
            df = pd.read_parquet(file, columns=['event_time_ns', 'message_type', 'mpid', 'symbol'])
            
            # Filter immediately
            df = df[df['message_type'].isin(['AddOrderMPID', 'Replace', 'Delete'])]
            
            if len(df) > 0:
                # Write filtered data to temp file
                temp_file = temp_dir / f"{date_str}_temp_{i:03d}.parquet"
                df.to_parquet(temp_file, compression='snappy')
                temp_files.append(temp_file)
                logger.info(f"    Filtered: {len(df):,} rows -> {temp_file.name}")
            
            del df  # Free memory immediately
            
        except Exception as e:
            logger.warning(f"    Skip: {e}")
    
    if not temp_files:
        logger.error(f"No data for {date_str}")
        return
    
    # Now combine temp files (they're much smaller)
    logger.info(f"  Combining {len(temp_files)} filtered files...")
    
    dfs = []
    for temp_file in temp_files:
        df = pd.read_parquet(temp_file)
        dfs.append(df)
    
    df_combined = pd.concat(dfs, ignore_index=True)
    
    # Sort
    logger.info(f"  Sorting {len(df_combined):,} events...")
    df_combined = df_combined.sort_values('event_time_ns').reset_index(drop=True)
    
    # Save
    output_file = nasdaq_dir / f"nasdaq_filtered_{date_str}.parquet"
    df_combined.to_parquet(output_file, compression='zstd', compression_level=3)
    
    # Cleanup temp files
    for temp_file in temp_files:
        temp_file.unlink()
    
    size_mb = output_file.stat().st_size / 1024 / 1024
    logger.info(f"  SUCCESS: {output_file.name} ({size_mb:.1f} MB, {len(df_combined):,} rows)\n")

if __name__ == '__main__':
    nasdaq_dir = Path("data/nasdaq")
    
    # All 10 days
    dates = [
        "20250310", "20250311", "20250312", "20250313", "20250314",
        "20250317", "20250318", "20250319", "20250320", "20250321"
    ]
    
    logger.info(f"Preprocessing {len(dates)} days...")
    for date_str in dates:
        preprocess_day(nasdaq_dir, date_str)
    
    logger.info("Done!")
