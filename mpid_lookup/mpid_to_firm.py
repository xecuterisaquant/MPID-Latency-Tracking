"""
MPID to Firm Name Mapping

Maps 4-character Market Participant IDs to their parent firms.
Sources: NASDAQ participant registry, firm disclosures, industry knowledge.
"""

MPID_TO_FIRM = {
    # Citadel Securities
    'CDRG': 'Citadel Securities',
    'CSTI': 'Citadel Securities',
    
    # Virtu Financial
    'NITE': 'Virtu Financial',
    'VIRT': 'Virtu Financial',
    'KCGM': 'Virtu Financial',
    
    # Jane Street
    'JNST': 'Jane Street',
    
    # Jump Trading
    'JSSF': 'Jump Trading',
    
    # IMC
    'IMCC': 'IMC',
    
    # Wolverine Trading
    'WCHV': 'Wolverine Trading',
    'WABR': 'Wolverine Trading',
    
    # Two Sigma
    'TSCM': 'Two Sigma Securities',
    
    # Hudson River Trading
    'HRTF': 'Hudson River Trading',
    
    # GTS
    'GTSM': 'GTS',
    
    # Susquehanna (SIG)
    'SGAS': 'Susquehanna (SIG)',
    
    # Flow Traders
    'FLTU': 'Flow Traders',
    
    # Traditional Broker-Dealers
    'JPMS': 'JP Morgan Securities',
    'GSCO': 'Goldman Sachs',
    'MLCO': 'Bank of America Merrill Lynch',
    'MSCO': 'Morgan Stanley',
    'UBSS': 'UBS Securities',
    'DBAB': 'Deutsche Bank',
    'CSFB': 'Credit Suisse',
    'FBCO': 'Credit Suisse',
    'BARC': 'Barclays',
    
    # Summit Securities Group (WBPX). NB: Wedbush's own MPIDs are WBSI/WEDP/WPRM.
    'WBPX': 'Summit Securities Group',
    'WBSI': 'Wedbush Securities',
    'WEDP': 'Wedbush Securities',
    'WPRM': 'Wedbush Securities',
    
    # Electronic Market Makers
    'ETMM': 'Electronic Trading & MM',
    
    # Regional Brokers
    'KEYB': 'Keefe, Bruyette & Woods',
    'CANT': 'Cantor Fitzgerald',
    'COWN': 'Cowen',
    'LEER': 'Leerink',
    'LEHM': 'Lehman Brothers (Legacy)',
    'BARD': 'Robert W. Baird',
    
    # Market Makers
    'XGWD': 'XGW Capital',
    'MAXM': 'Maxim Group',
    'INTL': 'Instinet',
    'RBCI': 'RBC Capital Markets',
    'BKCM': 'B. Riley',
    'CLST': 'Credit Suisse (Legacy)',
    'CHLM': 'Chalmers (Legacy)',
    'DADA': 'D.A. Davidson',
    'KING': 'King & Associates',
    'MGSN': 'Mischler Financial',
    'MLCF': 'Merrill Lynch',
    'NSDQ': 'Nasdaq OMX',
    'PEAK': 'Peak6',
    'PERT': 'Pershing',
    'RBCN': 'RBC',
    'RBIN': 'Robinhood',
    'SBSH': 'SunTrust Robinson Humphrey',
    'SEHO': 'Stifel Nicolaus',
    'STXG': 'Susquehanna',
    'TDRW': 'T. Rowe Price',
    'VNDM': 'Vanguard',
    'WAFD': 'Washington Federal',
    'WFII': 'Wells Fargo',
}

def get_firm_name(mpid: str) -> str:
    """Get firm name for an MPID, defaulting to the MPID itself if unknown."""
    return MPID_TO_FIRM.get(mpid, mpid)

def get_firm_category(firm: str) -> str:
    """
    Categorize firms by actual trading behavior (not corporate structure).
    Based on observed latency and activity patterns in the data.
    """
    # Dominant, ultra-fast market makers (14-17ms, 90%+ of activity)
    # These are the ACTUAL liquidity providers on these symbols
    active_fast_mm = {
        'Wolverine Trading',         # 16.6ms median, 35% of all activity
        'Summit Securities Group',   # 15.1ms median, 30% of all activity (MPID: WBPX)
        'JP Morgan Securities',      # 14.3ms median, 27% of all activity
    }
    
    # Sporadic/slow participants (3-6 seconds, <5% activity)
    # Known HFT firms but NOT active market makers on these symbols
    sporadic_slow = {
        'IMC', 'Citadel Securities', 'Virtu Financial', 'Flow Traders',
        'Susquehanna (SIG)', 'XGW Capital', 'Jane Street', 'Jump Trading',
        'Two Sigma Securities', 'Hudson River Trading', 'GTS',
        'Electronic Trading & MM'
    }
    
    # Traditional/agency brokers (slow, low activity)
    traditional_slow = {
        'Goldman Sachs', 'Bank of America Merrill Lynch', 'Morgan Stanley',
        'UBS Securities', 'Deutsche Bank', 'Credit Suisse', 'Barclays'
    }
    
    if firm in active_fast_mm:
        return 'Active Fast Market Maker'
    elif firm in sporadic_slow:
        return 'Sporadic/Slow HFT'
    elif firm in traditional_slow:
        return 'Traditional Broker'
    else:
        return 'Other'
