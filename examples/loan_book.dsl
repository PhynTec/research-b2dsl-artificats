contract "LoanBook" {
    struct Loan {
        borrower: address;
        amount: nat;
        deadline: nat
    }

    state:
        loans: map(nat -> Loan)

    event issue(loan_id: nat, borrower: address, amount: nat, deadline: nat) {
        where amount > 0
        do:
            loans[loan_id] := Loan { borrower: borrower; amount: amount; deadline: deadline }
    }

    event close(loan_id: nat, replacement: Loan) {
        where loans[loan_id].amount > 0
        do:
            loans[loan_id] := replacement
    }
}
