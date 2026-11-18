
"""Week 06–08 Graded Challenges: Strings, Lists, Tuples, and Dictionaries.

Complete the four functions below. Replace pass with your code.
Return results; do not use input().
Keep names and parameters unchanged so the automated tests can call them.
"""


# Challenge 1 (Strings): Count Vowels
# Return the total count of vowels ('a', 'e', 'i', 'o', 'u') in word, case-insensitive.
# Examples: count_vowels("apple") returns 2
#           count_vowels("Acibadem") returns 4
#           count_vowels("Python") returns 1
#           count_vowels("") returns 0
def count_vowels(word):
    count = 0
    for char in word.lower():
        if char in "aeiou":
            count += 1
    return count

"""Complete the four functions. Return results; do not use input().

Keep names and parameters unchanged. No imports are needed.
"""


# 1. Conditions: Use if / elif / else: below 10 → "cold", 10–25 → "warm", above 25 → "hot".
# temperature is a number; both 10 and 25 are warm.
def describe_temperature(temperature):
    if temperature < 10:
        return "cold"
    elif temperature <= 25:
        return "warm"
    else:
        return "hot"


# 2. For Loop: Use a for loop to count even positive integers from 1 through n.
# n is non-negative. Examples: 0 → 0, 5 → 2, 6 → 3.
def count_evens(n):
    count = 0
    for i in range(1, n + 1):
        if i % 2 == 0:
            count += 1
    return count


# 3. While Loop: Use a while loop to count how many times n can be halved (n // 2)
# until it reaches 1. Stop when n <= 1. n is an integer >= 1.
# Examples: 1 → 0, 2 → 1, 5 → 2, 16 → 4.
def halve_until_one(n):
    count = 0
    while n > 1:
        n = n // 2
        count += 1
    return count


# 4. Recursion: Use recursion to return 2 raised to power n, without ** or pow().
# n is a small non-negative integer. Examples: 0 → 1, 3 → 8.
def power_of_two(n):
    if n == 0:
        return 1
    return 2 * power_of_two(n - 1)


# Challenge 2 (Lists): Filter Positive Numbers
# Return a new list containing only the numbers strictly greater than 0,
# preserving the original order of elements.
# Examples: filter_positives([2, -3, 5, 0]) returns [2, 5]
#           filter_positives([-1, -2]) returns []
#           filter_positives([1, 2, 3]) returns [1, 2, 3]
def filter_positives(numbers):
    result = []
    for number in numbers:
        if number > 0:
            result.append(number)
    return result


# Challenge 3 (Tuples): Minimum and Maximum
# Return a tuple (smallest, largest) containing the minimum and maximum values
# from a non-empty list of numbers.
# Examples: min_max([3, 1, 4, 1, 5]) returns (1, 5)
#           min_max([42]) returns (42, 42)
#           min_max([-5, 0, 10]) returns (-5, 10)
def min_max(numbers):
    return (min(numbers), max(numbers))


# Challenge 4 (Dictionaries): Character Frequency Count
# Return a dictionary mapping each character in text to its occurrence count.
# Examples: count_characters("banana") returns {"b": 1, "a": 3, "n": 2}
#           count_characters("hello") returns {"h": 1, "e": 1, "l": 2, "o": 1}
#           count_characters("") returns {}
def count_characters(text):
    counts = {}
    for char in text:
        if char in counts:
            counts[char] += 1
        else:
            counts[char] = 1
    return counts
