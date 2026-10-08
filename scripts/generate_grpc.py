#!/usr/bin/env python3
"""
Generate Python gRPC code from proto files.
Run this script from the root of the repository.
"""

import subprocess
import sys
from pathlib import Path

# Root directory of the project
ROOT_DIR = Path(__file__).parent.parent
PROTO_DIR = ROOT_DIR / "proto"

# Services that need generated code
SERVICES = [
    "gateway",
    "services/workouts-service",
    "services/exercises-service",
    "services/plans-service",
    "services/rpe-service",
    "services/accounts-service",
]


def generate_proto_files(output_dir: Path):
    """Generate Python gRPC code from proto files."""
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all proto files
    proto_files = list(PROTO_DIR.glob("*.proto"))
    
    if not proto_files:
        print(f"No proto files found in {PROTO_DIR}")
        return False
    
    print(f"Found {len(proto_files)} proto files")
    
    # Build the grpc_tools.protoc command
    cmd = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"--proto_path={PROTO_DIR}",
        f"--python_out={output_dir}",
        f"--grpc_python_out={output_dir}",
    ] + [str(p) for p in proto_files]
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Proto generation successful")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Proto generation failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False


def main():
    """Main entry point."""
    print("Generating gRPC code from proto files...")
    
    # Generate for each service
    for service in SERVICES:
        service_path = ROOT_DIR / service
        if not service_path.exists():
            print(f"Service directory not found: {service_path}")
            continue
        
        output_dir = service_path / "proto_gen"
        print(f"\nGenerating for {service} -> {output_dir}")
        
        if not generate_proto_files(output_dir):
            print(f"Failed to generate for {service}")
            sys.exit(1)
    
    # Also generate in proto directory for shared usage
    shared_output = PROTO_DIR / "python"
    print(f"\nGenerating shared code -> {shared_output}")
    if not generate_proto_files(shared_output):
        print("Failed to generate shared code")
        sys.exit(1)
    
    print("\n✓ All proto files generated successfully")
    print("\nNote: Add the generated directories to PYTHONPATH or sys.path")
    print("For example: export PYTHONPATH=$PYTHONPATH:/path/to/proto_gen")


if __name__ == "__main__":
    main()
