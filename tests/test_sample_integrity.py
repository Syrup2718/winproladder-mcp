"""Guard the original WinProLadder exports against accidental modification."""

from hashlib import sha256
from pathlib import Path

SAMPLES_DIR = Path(__file__).parents[1] / "samples"

EXPECTED_SHA256 = {
    "test14.ldr": "5155c779d0a8bf2bf3fc6511ccd8287de95e266a75ba2dee07cb8caba92489b9",
    "test13.ldr": "c221aafbe6708f529680b537420d6733cc838cd8e8b4edb8dbff5129f247cb88",
    "test12.ldr": "ca61b33cf95e6af85cfe08dec0a6195fae475cad40330e3c00224389bd0caee5",
    "test11.ldr": "43f823427d4dfa69a0b6c09a833ea9c996ef7b8ae16e7b8d97531b171ffd4e4a",
    "test10.ldr": "0b00e0d1da4d7f466928f76921bd281d0c55158c32a5aa9ee41b373aa4cf3600",
    "test9.ldr": "4fa81b41f65d4d3901a56db53027224915f7a4eacd0a8f29028fed724b617e18",
    "test8.ldr": "e09ded354dd7ec34933bce7af7b992f920faf3de3fb95cdf2b12af2b32ee9a05",
    "test7.ldr": "cb7085f33a059f0eda2034ae9a18974249a49617b879b224cce0ab28057aed3c",
    "test6.ldr": "443500807d610cf2b459d1ea8bea00150e8dceeeae46b5750f3576b3df7d71e9",
    "test5.ldr": "2ccf0cbbdfe7952a30fbb4a51aec2923dadfe3bf06f22bf127a022a48da5a7a1",
    "test4.ldr": "ca91369c05f2973f9f1c037905a87e0eab64f5359c4bc9b966dc6decc2834c05",
    "test3.ldr": "f36360df0c748b938a57bf78ddbb8d99e57c58e8160e347a1484b6dd0459fb11",
    "test.ldr": "7c1d667ce04129cf8fdefa5695158385c5e9e7b02ed8423c0c6aaf5553976d29",
    "test2.ldr": "2f5900459a3ceb819e8c763b98b5b73ee115c1e5122be6302be627816820a2e3",
    "w1.ldr": "c34bc1402c0e63ad2670d82a3b0439c573d99c4b95467739a31eff5701dee226",
}


def test_ground_truth_samples_are_unchanged() -> None:
    actual_files = {path.name for path in SAMPLES_DIR.glob("*.ldr")}
    assert actual_files == EXPECTED_SHA256.keys()

    for filename, expected_hash in EXPECTED_SHA256.items():
        content = (SAMPLES_DIR / filename).read_bytes()
        assert sha256(content).hexdigest() == expected_hash, filename
