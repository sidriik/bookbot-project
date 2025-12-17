import unittest
from project1 import User


class TestUser(unittest.TestCase):

    def setUp(self):
        self.user = User()

    def test_add_book_success(self):
        result = self.user.add_book(1, 101, "planned")
        assert result == True

    def test_add_book_invalid_status(self):
        result = self.user.add_book(1, 100, "invalid")
        self.assertFalse(result)

    def test_rate_book_success(self):
        self.user.add_book(1, 101, "planned")
        result = self.user.rate_book(1, 101, 5)
        assert result == True

    def test_rate_book_invalid_rating(self):
        self.user.add_book(1, 101, "planned")
        result=self.user.rate_book(1, 101, 0)
        self.assertFalse(result)

    def test_get_status_success(self):
        self.user.add_book(1, 101, "planned")
        self.user.add_book(1, 102, "reading")
        stats = self.user.get_status(1)
        assert stats['total'] == 2

    def test_get_status_empty(self):
        stats = self.user.get_status(999)
        assert stats['total'] == 0

    def test_remove_book_success(self):
        self.user.add_book(1, 101, "planned")
        result = self.user.remove_book(1, 101)
        assert result == True

    def test_remove_book_not_found(self):
        result = self.user.remove_book(1, 101)
        assert result == False

    def test_has_book_true(self):
        self.user.add_book(1, 101, "planned")
        result = self.user.has_book(1, 101)
        assert result == True

    def test_has_book_false(self):
        result = self.user.has_book(1, 101)
        assert result == False


if __name__ == "__main__":
    unittest.main()
