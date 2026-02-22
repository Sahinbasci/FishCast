"""P0: Wind normalization tests (G3)."""

from app.utils.wind import degrees_to_cardinal_8, normalize_cardinal_8


class TestDegreesToCardinal8:
    def test_north(self):
        assert degrees_to_cardinal_8(0) == "N"
        assert degrees_to_cardinal_8(360) == "N"

    def test_near_north(self):
        assert degrees_to_cardinal_8(10) == "N"
        assert degrees_to_cardinal_8(350) == "N"

    def test_northeast(self):
        assert degrees_to_cardinal_8(30) == "NE"
        assert degrees_to_cardinal_8(45) == "NE"
        assert degrees_to_cardinal_8(60) == "NE"

    def test_east(self):
        assert degrees_to_cardinal_8(90) == "E"

    def test_south_southwest(self):
        assert degrees_to_cardinal_8(200) in ("S", "SW")

    def test_northwest(self):
        assert degrees_to_cardinal_8(315) == "NW"

    def test_all_8_directions(self):
        expected = [
            (0, "N"), (45, "NE"), (90, "E"), (135, "SE"),
            (180, "S"), (225, "SW"), (270, "W"), (315, "NW"),
        ]
        for deg, card in expected:
            assert degrees_to_cardinal_8(deg) == card, f"{deg}° should be {card}"


class TestNormalizeCardinal8:
    def test_16_to_8_mappings(self):
        assert normalize_cardinal_8("NNE") == "NE"
        assert normalize_cardinal_8("ENE") == "NE"
        assert normalize_cardinal_8("ESE") == "SE"
        assert normalize_cardinal_8("SSE") == "SE"
        assert normalize_cardinal_8("SSW") == "SW"
        assert normalize_cardinal_8("WSW") == "SW"
        assert normalize_cardinal_8("WNW") == "NW"
        assert normalize_cardinal_8("NNW") == "NW"

    def test_passthrough_canonical(self):
        for card in ("N", "NE", "E", "SE", "S", "SW", "W", "NW"):
            assert normalize_cardinal_8(card) == card

    def test_case_insensitive(self):
        assert normalize_cardinal_8("nne") == "NE"
        assert normalize_cardinal_8("sw") == "SW"
        assert normalize_cardinal_8("  NE  ") == "NE"
