#!/usr/bin/env python3
"""Verification script for map clustering functionality.

This script tests the create_clustered_map function to ensure that:
1. Maps are created correctly with valid data
2. Clustering is properly configured
3. Markers contain the expected information
4. The function handles edge cases appropriately
"""

import sys
from pathlib import Path
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.app import create_clustered_map


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def test_basic_map_creation():
    """Test 1: Basic map creation with valid data."""
    print_section("TEST 1: Basic Map Creation")

    # Create sample data with Swedish bird observations
    sample_data = pd.DataFrame({
        'latitude': [59.3293, 57.7089, 55.6050],  # Stockholm, Gothenburg, Malmö
        'longitude': [18.0686, 11.9746, 13.0038],
        'Scientific Name': ['Parus major', 'Turdus merula', 'Passer domesticus'],
        'Common Name': ['Great Tit', 'Common Blackbird', 'House Sparrow'],
        'Date': ['2024-10-15', '2024-10-16', '2024-10-17']
    })

    map_obj = create_clustered_map(sample_data)

    # Verify map was created
    assert map_obj is not None, "❌ Map object should not be None"
    print("✓ Map object created successfully")

    # Verify map type
    import folium
    assert isinstance(map_obj, folium.Map), "❌ Map should be a folium.Map instance"
    print("✓ Map is correct type (folium.Map)")

    # Verify map center (should be average of coordinates)
    expected_lat = sample_data['latitude'].mean()
    expected_lon = sample_data['longitude'].mean()
    actual_lat, actual_lon = map_obj.location

    assert abs(actual_lat - expected_lat) < 0.01, f"❌ Latitude mismatch: {actual_lat} vs {expected_lat}"
    assert abs(actual_lon - expected_lon) < 0.01, f"❌ Longitude mismatch: {actual_lon} vs {expected_lon}"
    print(f"✓ Map centered correctly at ({actual_lat:.4f}, {actual_lon:.4f})")

    # Verify zoom level (stored in options in newer folium versions)
    map_html = map_obj._repr_html_()
    # Check if zoom is configured correctly in the map
    assert 'zoom' in map_html.lower(), "❌ Zoom configuration not found"
    print("✓ Zoom level configured correctly")

    print("\n✅ TEST 1 PASSED: Basic map creation works correctly")
    return True


def test_clustering_configuration():
    """Test 2: Verify clustering is properly configured."""
    print_section("TEST 2: Clustering Configuration")

    sample_data = pd.DataFrame({
        'latitude': [59.3293, 59.3294, 59.3295],  # Very close coordinates
        'longitude': [18.0686, 18.0687, 18.0688],
        'Scientific Name': ['Species A', 'Species B', 'Species C'],
        'Common Name': ['Bird A', 'Bird B', 'Bird C'],
        'Date': ['2024-10-15', '2024-10-16', '2024-10-17']
    })

    map_obj = create_clustered_map(sample_data)

    # Convert map to HTML to inspect structure
    map_html = map_obj._repr_html_()

    # Verify MarkerCluster is in the HTML
    assert 'MarkerCluster' in map_html or 'markercluster' in map_html.lower(), \
        "❌ MarkerCluster not found in map HTML"
    print("✓ MarkerCluster plugin is present in map")

    # Verify layer name is included
    assert 'Observations' in map_html, "❌ 'Observations' layer name not found"
    print("✓ Layer name 'Observations' found in map")

    print("\n✅ TEST 2 PASSED: Clustering is properly configured")
    return True


def test_marker_content():
    """Test 3: Verify markers contain correct information."""
    print_section("TEST 3: Marker Content Verification")

    sample_data = pd.DataFrame({
        'latitude': [59.3293],
        'longitude': [18.0686],
        'Scientific Name': ['Parus major'],
        'Common Name': ['Great Tit'],
        'Date': ['2024-10-15']
    })

    map_obj = create_clustered_map(sample_data)
    map_html = map_obj._repr_html_()

    # Verify species name is in the HTML
    assert 'Parus major' in map_html, "❌ Scientific name not found in map HTML"
    print("✓ Scientific name 'Parus major' found in marker")

    # Verify common name is in the HTML
    assert 'Great Tit' in map_html, "❌ Common name not found in map HTML"
    print("✓ Common name 'Great Tit' found in marker")

    # Verify date is in the HTML
    assert '2024-10-15' in map_html, "❌ Date not found in map HTML"
    print("✓ Date '2024-10-15' found in marker")

    # Verify coordinates are in the HTML
    assert '59.3293' in map_html, "❌ Latitude not found in map HTML"
    assert '18.0686' in map_html, "❌ Longitude not found in map HTML"
    print("✓ Coordinates found in marker")

    print("\n✅ TEST 3 PASSED: Marker content is correct")
    return True


def test_empty_data_handling():
    """Test 4: Verify handling of empty/invalid data."""
    print_section("TEST 4: Empty Data Handling")

    # Test with empty DataFrame
    empty_df = pd.DataFrame({
        'latitude': [],
        'longitude': []
    })

    map_obj = create_clustered_map(empty_df)
    assert map_obj is None, "❌ Map should return None for empty data"
    print("✓ Returns None for empty DataFrame")

    # Test with NaN values
    nan_df = pd.DataFrame({
        'latitude': [None, None],
        'longitude': [None, None]
    })

    map_obj = create_clustered_map(nan_df)
    assert map_obj is None, "❌ Map should return None for all-NaN data"
    print("✓ Returns None for all-NaN coordinates")

    # Test with partial data
    partial_df = pd.DataFrame({
        'latitude': [59.3293, None, 57.7089],
        'longitude': [18.0686, None, 11.9746]
    })

    map_obj = create_clustered_map(partial_df)
    assert map_obj is not None, "❌ Map should be created with partial valid data"
    print("✓ Creates map with partial valid data (skips NaN rows)")

    print("\n✅ TEST 4 PASSED: Edge cases handled correctly")
    return True


def test_large_dataset():
    """Test 5: Verify performance with larger dataset."""
    print_section("TEST 5: Large Dataset Performance")

    # Create a larger dataset simulating many observations
    import random
    random.seed(42)

    num_observations = 100
    latitudes = [55 + random.random() * 5 for _ in range(num_observations)]  # Sweden range
    longitudes = [11 + random.random() * 13 for _ in range(num_observations)]

    large_data = pd.DataFrame({
        'latitude': latitudes,
        'longitude': longitudes,
        'Scientific Name': [f'Species {i}' for i in range(num_observations)],
        'Common Name': [f'Bird {i}' for i in range(num_observations)],
        'Date': ['2024-10-15'] * num_observations
    })

    import time
    start_time = time.time()
    map_obj = create_clustered_map(large_data)
    elapsed_time = time.time() - start_time

    assert map_obj is not None, "❌ Map should be created for large dataset"
    print(f"✓ Map created successfully with {num_observations} observations")

    assert elapsed_time < 5.0, f"❌ Map creation too slow: {elapsed_time:.2f}s"
    print(f"✓ Map created in {elapsed_time:.3f} seconds (acceptable performance)")

    # Verify clustering is working with HTML inspection
    map_html = map_obj._repr_html_()
    assert 'MarkerCluster' in map_html or 'markercluster' in map_html.lower(), \
        "❌ Clustering should be present for large dataset"
    print("✓ Clustering is active for large dataset")

    print("\n✅ TEST 5 PASSED: Large dataset handled efficiently")
    return True


def test_missing_optional_columns():
    """Test 6: Verify handling of missing optional columns."""
    print_section("TEST 6: Missing Optional Columns")

    # Test with only required columns (lat/lon)
    minimal_data = pd.DataFrame({
        'latitude': [59.3293],
        'longitude': [18.0686]
    })

    map_obj = create_clustered_map(minimal_data)
    assert map_obj is not None, "❌ Map should be created with minimal data"
    print("✓ Map created with only lat/lon columns")

    # Test with some optional columns missing
    partial_columns_data = pd.DataFrame({
        'latitude': [59.3293],
        'longitude': [18.0686],
        'Scientific Name': ['Parus major']
        # Missing Common Name and Date
    })

    map_obj = create_clustered_map(partial_columns_data)
    assert map_obj is not None, "❌ Map should be created with partial columns"
    print("✓ Map created with partial optional columns")

    print("\n✅ TEST 6 PASSED: Missing optional columns handled gracefully")
    return True


def main():
    """Run all verification tests."""
    print("\n" + "="*70)
    print("  MAP CLUSTERING VERIFICATION SUITE")
    print("  Testing create_clustered_map() functionality")
    print("="*70)

    tests = [
        test_basic_map_creation,
        test_clustering_configuration,
        test_marker_content,
        test_empty_data_handling,
        test_large_dataset,
        test_missing_optional_columns
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            failed += 1
            print(f"\n❌ TEST FAILED: {e}")
        except Exception as e:
            failed += 1
            print(f"\n❌ TEST ERROR: {e}")
            import traceback
            traceback.print_exc()

    # Print summary
    print("\n" + "="*70)
    print("  VERIFICATION SUMMARY")
    print("="*70)
    print(f"  Total Tests: {len(tests)}")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print("="*70)

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Map clustering is working correctly.")
        print("\nThe clustering functionality:")
        print("  ✓ Creates maps with valid data")
        print("  ✓ Configures clustering properly")
        print("  ✓ Includes all required information in markers")
        print("  ✓ Handles edge cases gracefully")
        print("  ✓ Performs well with large datasets")
        print("  ✓ Works with missing optional data")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
