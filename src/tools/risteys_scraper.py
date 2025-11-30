import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional

RISTEYS_BASE_URL = "https://risteys.finngen.fi"

def search_risteys(keyword: str) -> Dict[str, Any]:
    """
    Searches Risteys for a phenotype or keyword and returns a summary.
    
    Args:
        keyword: The phenotype code (e.g. 'K51') or name to search for.
        
    Returns:
        A dictionary containing the title, description, and key statistics.
    """
    # First, try to access the phenocode page directly if it looks like a code
    if keyword.isalnum() and len(keyword) < 10:
        url = f"{RISTEYS_BASE_URL}/phenocode/{keyword}"
        response = requests.get(url)
        if response.status_code == 200:
            return _parse_phenocode_page(response.text, url)
            
    # Fallback: Use the search endpoint (simulated here by checking if direct access failed)
    # In a real scenario, we might need to use their search API or scrape the search results page.
    # For this MVP, we'll assume the user provides a valid phenocode or we fail gracefully.
    
    return {
        "status": "not_found",
        "message": f"Could not find direct page for '{keyword}'. Please try a valid Phenocode (e.g., 'K51')."
    }

def _parse_phenocode_page(html_content: str, url: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract Title (Phenotype Name)
    title_elem = soup.find('h1')
    title = title_elem.get_text(strip=True) if title_elem else "Unknown Phenotype"
    
    # Extract Description (Long name or definition)
    # Risteys structure varies, but usually there's a description block
    desc_elem = soup.find('div', {'id': 'description'})
    description = desc_elem.get_text(strip=True) if desc_elem else "No description available."
    
    # Extract Stats (N cases, etc.)
    stats = {}
    stats_grid = soup.find('div', {'id': 'summary_stats'})
    if stats_grid:
        for item in stats_grid.find_all('div', class_='stat-item'):
            label = item.find('div', class_='stat-label')
            value = item.find('div', class_='stat-value')
            if label and value:
                stats[label.get_text(strip=True)] = value.get_text(strip=True)
                
    return {
        "status": "success",
        "url": url,
        "title": title,
        "description": description,
        "stats": stats
    }

if __name__ == "__main__":
    # Test
    print(search_risteys("K51"))
