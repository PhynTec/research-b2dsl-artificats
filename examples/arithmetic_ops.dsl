// Regression example for multiplication, integer division, and modulo.
contract "ArithmeticOps" {
    state:
        product: nat
        quotient: nat
        remainder: nat

    invariants:
        product >= 0;
        quotient >= 0;
        remainder >= 0

    event calculate(left: nat, right: nat, divisor: nat) {
        where divisor > 0
        do:
            product := left * right,
            quotient := left / divisor,
            remainder := left % divisor
    }
}
