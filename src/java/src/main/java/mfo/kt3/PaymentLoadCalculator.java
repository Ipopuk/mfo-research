package mfo.kt3;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;
import java.util.Objects;

public final class PaymentLoadCalculator {
    public record Result(String status, BigDecimal monthlyIncome, BigDecimal existingPayments,
                         BigDecimal paymentSharePercent) {
        public boolean calculated() { return paymentSharePercent != null; }
    }

    public Result calculate(Applicant applicant, List<Income> incomes, List<Obligation> obligations,
                            BigDecimal proposedMonthlyPayment) {
        if (proposedMonthlyPayment.signum() < 0) {
            throw new IllegalArgumentException("Предложенный платёж не может быть отрицательным");
        }

        BigDecimal monthlyIncome = BigDecimal.ZERO;
        for (Income income : incomes) {
            if (Objects.equals(income.applicantId(), applicant.id()) && income.verified()) {
                BigDecimal amount = income.monthlyAmount();
                if (amount == null) {
                    throw new IllegalArgumentException("Поле monthly_amount записи дохода "
                        + income.id() + " должно быть числом");
                }
                monthlyIncome = monthlyIncome.add(amount);
            }
        }

        BigDecimal existingPayments = BigDecimal.ZERO;
        for (Obligation obligation : obligations) {
            if (Objects.equals(obligation.applicantId(), applicant.id()) && obligation.active()) {
                BigDecimal payment = obligation.monthlyPayment();
                if (payment == null) {
                    throw new IllegalArgumentException("Поле monthly_payment записи обязательства "
                        + obligation.id() + " должно быть числом");
                }
                existingPayments = existingPayments.add(payment);
            }
        }

        if (monthlyIncome.signum() <= 0) {
            return new Result("insufficient_income_data", monthlyIncome, existingPayments, null);
        }
        BigDecimal share = existingPayments.add(proposedMonthlyPayment).movePointRight(2)
            .divide(monthlyIncome, 1, RoundingMode.HALF_EVEN);
        return new Result("calculated", monthlyIncome, existingPayments, share);
    }
}
