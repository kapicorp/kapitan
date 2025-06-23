package main

input: {
	numerator:   int
	denominator: int & !=0
}

output: {
	result: input.numerator / input.denominator
}
