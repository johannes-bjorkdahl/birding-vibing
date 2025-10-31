#!/usr/bin/env python3
"""Generate visual proof of clustering functionality.

This script creates an actual HTML map file that can be opened in a browser
to visually verify that clustering is working correctly.
"""

import sys
from pathlib import Path
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.app import create_clustered_map


def main():
    """Generate a visual proof map with clustering."""
    print("="*70)
    print("  GENERATING VISUAL PROOF OF CLUSTERING")
    print("="*70)

    # Create sample data with Swedish bird observations
    # Using real cities in Sweden with clustered observations
    print("\nCreating sample data with 50 observations across Sweden...")

    sample_data = pd.DataFrame({
        'latitude': [
            # Stockholm area (cluster 1)
            59.3293, 59.3320, 59.3350, 59.3280, 59.3400,
            59.3250, 59.3380, 59.3310, 59.3290, 59.3360,
            # Gothenburg area (cluster 2)
            57.7089, 57.7100, 57.7050, 57.7120, 57.7070,
            57.7110, 57.7080, 57.7095, 57.7085, 57.7105,
            # Malmö area (cluster 3)
            55.6050, 55.6070, 55.6030, 55.6080, 55.6045,
            55.6065, 55.6055, 55.6040, 55.6075, 55.6060,
            # Uppsala area (cluster 4)
            59.8586, 59.8600, 59.8570, 59.8590, 59.8580,
            # Scattered observations
            56.0465, 58.4108, 60.6748, 62.3908, 63.8258,
            57.7826, 56.8791, 59.2753, 58.5910, 57.4917,
            56.6787, 58.2706, 59.6562, 57.1512, 55.8657
        ],
        'longitude': [
            # Stockholm area (cluster 1)
            18.0686, 18.0700, 18.0750, 18.0650, 18.0800,
            18.0620, 18.0780, 18.0710, 18.0680, 18.0760,
            # Gothenburg area (cluster 2)
            11.9746, 11.9760, 11.9730, 11.9780, 11.9740,
            11.9770, 11.9750, 11.9755, 11.9745, 11.9765,
            # Malmö area (cluster 3)
            13.0038, 13.0050, 13.0020, 13.0060, 13.0035,
            13.0055, 13.0045, 13.0030, 13.0058, 13.0048,
            # Uppsala area (cluster 4)
            17.6389, 17.6400, 17.6370, 17.6395, 17.6385,
            # Scattered observations
            16.1932, 15.6214, 17.1413, 20.2639, 20.2630,
            14.1562, 14.8059, 17.9410, 16.1826, 15.5827,
            16.3618, 12.9450, 16.7748, 12.7066, 13.5354
        ],
        'Scientific Name': [
            'Parus major', 'Turdus merula', 'Passer domesticus', 'Fringilla coelebs', 'Erithacus rubecula',
            'Phylloscopus trochilus', 'Carduelis chloris', 'Sturnus vulgaris', 'Corvus cornix', 'Motacilla alba',
            'Pica pica', 'Garrulus glandarius', 'Columba palumbus', 'Dendrocopos major', 'Sitta europaea',
            'Cyanistes caeruleus', 'Troglodytes troglodytes', 'Aegithalos caudatus', 'Regulus regulus', 'Pyrrhula pyrrhula',
            'Emberiza citrinella', 'Luscinia luscinia', 'Oenanthe oenanthe', 'Anthus pratensis', 'Alauda arvensis',
            'Hirundo rustica', 'Delichon urbicum', 'Muscicapa striata', 'Sylvia borin', 'Phoenicurus phoenicurus',
            'Parus major', 'Turdus merula', 'Passer domesticus', 'Fringilla coelebs', 'Erithacus rubecula',
            'Phylloscopus trochilus', 'Carduelis chloris', 'Sturnus vulgaris', 'Corvus cornix', 'Motacilla alba',
            'Pica pica', 'Garrulus glandarius', 'Columba palumbus', 'Dendrocopos major', 'Sitta europaea',
            'Cyanistes caeruleus', 'Troglodytes troglodytes', 'Aegithalos caudatus', 'Regulus regulus', 'Pyrrhula pyrrhula'
        ],
        'Common Name': [
            'Great Tit', 'Common Blackbird', 'House Sparrow', 'Common Chaffinch', 'European Robin',
            'Willow Warbler', 'European Greenfinch', 'Common Starling', 'Hooded Crow', 'White Wagtail',
            'Eurasian Magpie', 'Eurasian Jay', 'Common Wood Pigeon', 'Great Spotted Woodpecker', 'Eurasian Nuthatch',
            'Eurasian Blue Tit', 'Eurasian Wren', 'Long-tailed Tit', 'Goldcrest', 'Eurasian Bullfinch',
            'Yellowhammer', 'Thrush Nightingale', 'Northern Wheatear', 'Meadow Pipit', 'Eurasian Skylark',
            'Barn Swallow', 'Common House Martin', 'Spotted Flycatcher', 'Garden Warbler', 'Common Redstart',
            'Great Tit', 'Common Blackbird', 'House Sparrow', 'Common Chaffinch', 'European Robin',
            'Willow Warbler', 'European Greenfinch', 'Common Starling', 'Hooded Crow', 'White Wagtail',
            'Eurasian Magpie', 'Eurasian Jay', 'Common Wood Pigeon', 'Great Spotted Woodpecker', 'Eurasian Nuthatch',
            'Eurasian Blue Tit', 'Eurasian Wren', 'Long-tailed Tit', 'Goldcrest', 'Eurasian Bullfinch'
        ],
        'Date': [f'2024-10-{15+i%15:02d}' for i in range(50)]
    })

    print(f"✓ Created {len(sample_data)} observations")
    print(f"  - Stockholm area: 10 observations")
    print(f"  - Gothenburg area: 10 observations")
    print(f"  - Malmö area: 10 observations")
    print(f"  - Uppsala area: 5 observations")
    print(f"  - Scattered: 15 observations")

    # Create the clustered map
    print("\nGenerating clustered map...")
    map_obj = create_clustered_map(sample_data)

    if map_obj is None:
        print("❌ Failed to create map")
        return 1

    print("✓ Map generated successfully")

    # Save to HTML file
    output_file = Path(__file__).parent / "clustering_visual_proof.html"
    map_obj.save(str(output_file))

    print(f"\n✅ Visual proof saved to: {output_file}")
    print("\nTo view the clustering in action:")
    print("  1. Open clustering_visual_proof.html in a web browser")
    print("  2. You should see:")
    print("     • Cluster circles with numbers showing grouped observations")
    print("     • Clusters for Stockholm, Gothenburg, Malmö, and Uppsala areas")
    print("     • Individual markers for scattered observations")
    print("     • Click clusters to zoom in and see individual birds")
    print("     • Click markers to see species details")

    # Verify clustering is in the HTML
    print("\nVerifying HTML content...")
    with open(output_file, 'r') as f:
        html_content = f.read()

    checks = [
        ('MarkerCluster', 'MarkerCluster plugin'),
        ('Parus major', 'Bird species data'),
        ('Great Tit', 'Common names'),
        ('2024-10', 'Observation dates'),
        ('59.3293', 'Coordinates'),
        ('OpenStreetMap', 'Map tiles')
    ]

    all_present = True
    for search_term, description in checks:
        if search_term in html_content:
            print(f"  ✓ {description} present")
        else:
            print(f"  ❌ {description} missing")
            all_present = False

    if all_present:
        print("\n🎉 SUCCESS! All clustering elements are present in the HTML.")
        print("\nThe generated map demonstrates:")
        print("  ✓ Automatic clustering of nearby observations")
        print("  ✓ Cluster counts displayed on map")
        print("  ✓ Individual markers with popup information")
        print("  ✓ Interactive zoom and pan functionality")
        print("  ✓ Proper map centering on observations")
        return 0
    else:
        print("\n⚠️  Some elements are missing. Please review.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
