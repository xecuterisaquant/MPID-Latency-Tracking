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
    
    # Wedbush
    'WBPX': 'Wedbush Securities',
    
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
    """Categorize firms by business model."""
    hft_firms = {
        'Citadel Securities', 'Virtu Financial', 'Jane Street', 'Jump Trading',
        'IMC', 'Wolverine Trading', 'Two Sigma Securities', 'Hudson River Trading',
        'GTS', 'Susquehanna (SIG)', 'Flow Traders', 'XGW Capital'
    }
    
    traditional_brokers = {
        'JP Morgan Securities', 'Goldman Sachs', 'Bank of America Merrill Lynch',
        'Morgan Stanley', 'UBS Securities', 'Deutsche Bank', 'Credit Suisse',
        'Barclays', 'Wedbush Securities'
    }
    
    if firm in hft_firms:
        return 'HFT / Market Maker'
    elif firm in traditional_brokers:
        return 'Traditional Broker-Dealer'
    else:
        return 'Other'
