"""Guard the original WinProLadder exports against accidental modification."""

from hashlib import sha256
from pathlib import Path

SAMPLES_DIR = Path(__file__).parents[1] / "samples"

EXPECTED_SHA256 = {
    "test27.ldr": "e6edf47845aecb35a2a8441250c61de110725a68c74143ca59368f939629e734",
    "test26.ldr": "ef51137d5b53a130e99afd213b1c646166db3de14ad4a507aaafe42cbc1a80f3",
    "test25.ldr": "ee988f7f2c051931529f306a89119399c4885112fe30c4c1fb866fe4d92eaf11",
    "test24.ldr": "01690fde5c181da0ad3b1eb1958fec73264d25dfbadc887e78dec4b1f78b95b9",
    "test23.ldr": "31642eb09039ab57dd5c3d09491865a24ba6e6266aa92f1452b50be7234faa34",
    "test22.ldr": "6eff04db1f6734fbb1592fb082d26388df243284b05d3a42acefae9d1503826d",
    "test21.ldr": "1bea9772444fbb0e05b1d21a6b9518c0f212a059f33ad92ac187c187e54ac3f0",
    "test20.ldr": "0bc52a62afb0260addd18e7e9a547c377ca900f3c9c6c84aea76a429773fcf62",
    "test19.ldr": "8cca55d040a1a3bdf8de59872e63bef8f32b102a57a28522b0c781d07fb7be54",
    "test18.ldr": "dfed9bcdbc5999fafa7f0edfa5edcc70d5800e5efb7d9c0faf21274977dae14c",
    "test17.ldr": "d8b9f6d8ad1d4e1364bb2707e1005ef93d48f59e367cfadbc506842845aad2ab",
    "test16.ldr": "34d612e432e516587e28ffb45bb41ddfe245a67e29f948105f1c55380e716217",
    "test15.ldr": "587d2bcff2794470be5524cf85355f2d74f303cf9d7213a4f26f6d3f92c73c1f",
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
