import argparse
import os
import subprocess
import sys


SCRIPT_MAP = {
    "validate": "validator.py",
    "validate-all": "validate_all.py",
    "pipeline": "orchestrator.py",
    "zip": "zip_models.py",
    "fix-zip": "fix_and_zip_models.py",
    "gen-mil-symbols": "gen_mil_symbols.py",
    "fetch-assets": "fetch_and_gen_assets.py",
    "gen-vehicles": "generate_vehicle_packages.py",
    "gen-fighters": "gen_fighter_packages.py",
    "gen-carriers": "gen_carrier_packages.py",
    "gen-sm3": "gen_sm3_pipeline.py",
    "gen-y20": "gen_y20_package.py",
    "gen-y5": "gen_y5_package.py",
    "gen-fujian": "gen_fujian_carrier_package.py",
    "gen-liaoning": "gen_liaoning_carrier_package.py",
    "gen-shandong": "gen_shandong_carrier_package.py",
    "gen-ford": "gen_gerald_ford_carrier_package.py",
    "gen-nimitz": "gen_nimitz_carrier_package.py",
    "gen-reagan": "gen_ronald_reagan_carrier_package.py",
    "gen-queen-elizabeth": "gen_queen_elizabeth_carrier_package.py",
    "gen-charles-de-gaulle": "gen_charles_de_gaulle_carrier_package.py",
    "gen-america-lha6": "gen_america_lha6_package.py",
    "gen-izumo": "gen_izumo_ddh183_package.py",
    "gen-burke": "gen_arleigh_burke_destroyer_package.py",
    "gen-type055": "gen_type055_destroyer_package.py",
    "gen-type052d": "gen_type052d_destroyer_package.py",
    "gen-type45": "gen_type45_destroyer_package.py",
    "gen-zumwalt": "gen_zumwalt_destroyer_package.py",
    "gen-type054a": "gen_type054a_frigate_package.py",
    "gen-type056a": "gen_type056a_frigate_package.py",
    "gen-virginia-sub": "gen_virginia_submarine_package.py",
    "gen-ssgn-sub": "gen_ssgn_submarine_package.py",
    "gen-type093b-sub": "gen_type093b_submarine_package.py",
    "gen-type039ab-sub": "gen_type039ab_submarine_package.py",
    "gen-type212a214-sub": "gen_type212a_214_submarine_package.py",
    "gen-belgorod-sub": "gen_belgorod_poseidon_submarine_package.py",
    "gen-orca-xluuv": "gen_orca_xluuv_package.py",
    "gen-hsu001-uuv": "gen_hsu001_uuv_package.py",
    "gen-aim120": "gen_aim120_package.py",
    "gen-aim9x": "gen_aim9x_package.py",
    "gen-pl15": "gen_pl15_package.py",
    "gen-aim54": "gen_aim54_package.py",
    "gen-df15b": "gen_df15b_package.py",
    "gen-df15c": "gen_df15c_package.py",
    "gen-nsm": "gen_nsm_package.py",
    "gen-hj10": "gen_hj10_package.py",
    "gen-hj12": "gen_hj12_package.py",
    "gen-yj18": "gen_yj18_package.py",
    "gen-agm158": "gen_agm158_package.py",
    "gen-agm88": "gen_agm88_package.py",
    "gen-switchblade300": "gen_switchblade300_package.py",
    "gen-xq58a": "gen_xq58a_package.py",
    "gen-gbu32": "gen_gbu32_package.py",
    "gen-gbu12": "gen_gbu12_package.py",
    "gen-gbu39": "gen_gbu39_package.py",
    "gen-gbu31": "gen_gbu31_package.py",
    "gen-m777a2": "gen_m777a2_package.py",
    "gen-m795": "gen_m795_package.py",
    "gen-constellation": "gen_constellation_frigate_package.py",
    "gen-fremm": "gen_fremm_frigate_package.py",
    "gen-22350": "gen_project22350_frigate_package.py",
    "gen-type26": "gen_type26_frigate_package.py",
    "gen-30ffm": "gen_30ffm_frigate_package.py",
    "gen-y9": "gen_y9_package.py",
    "gen-y9g": "gen_y9g_package.py",
    "gen-c130j": "gen_c130j_package.py",
    "gen-ec130h": "gen_ec130h_package.py",
    "gen-ec37b": "gen_ec37b_package.py",
    "gen-c17": "gen_c17_package.py",
    "gen-ea18g": "gen_ea18g_package.py",
    "gen-j15d": "gen_j15d_package.py",
    "gen-j16d": "gen_j16d_package.py",
    "gen-il76md90a": "gen_il76md90a_package.py",
    "gen-z8l": "gen_z8l_package.py",
    "gen-z10": "gen_z10_package.py",
    "gen-z20": "gen_z20_package.py",
    "gen-ah64e": "gen_ah64e_package.py",
    "gen-uh60m": "gen_uh60m_package.py",
    "gen-ch47f": "gen_ch47f_package.py",
    "gen-ch53k": "gen_ch53k_package.py",
    "gen-mengshi": "gen_mengshi_gen3_package.py",
    "gen-type99": "gen_type99_tank_package.py",
    "gen-35mm-spaag": "gen_35mm_wheeled_spaag_package.py",
    "gen-ahead": "gen_ahead_round_package.py",
    "fetch-images": "fetch_images.py",
}


def run_script(script_name, extra_args):
    script = SCRIPT_MAP[script_name]
    script_path = os.path.join(os.path.dirname(__file__), script)
    if extra_args and extra_args[0] == "--":
        extra_args = extra_args[1:]
    cmd = [sys.executable, script_path, *extra_args]
    print("Running:", " ".join(cmd))
    return subprocess.run(cmd, check=False).returncode


def build_parser():
    parser = argparse.ArgumentParser(
        description="Unified CLI for AIAgentData model generation and packaging."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in SCRIPT_MAP:
        sub = subparsers.add_parser(name, help=f"Run {SCRIPT_MAP[name]}")
        sub.add_argument(
            "args",
            nargs=argparse.REMAINDER,
            help="Arguments passed through to the target script.",
        )

    list_cmd = subparsers.add_parser("list", help="List available commands")
    list_cmd.set_defaults(command="list")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "list":
        print("Available commands:")
        for name, script in sorted(SCRIPT_MAP.items()):
            print(f"  {name:15s} -> {script}")
        return 0

    passthrough = args.args if hasattr(args, "args") else []
    return run_script(args.command, passthrough)


if __name__ == "__main__":
    raise SystemExit(main())
