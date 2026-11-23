package mfo.kt3;

import java.math.BigDecimal;
import java.math.MathContext;
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
                monthlyIncome = monthlyIncome.add(income.monthlyAmount());
            }
        }

        BigDecimal existingPayments = BigDecimal.ZERO;
        for (Obligation obligation : obligations) {
            if (Objects.equals(obligation.applicantId(), applicant.id()) && obligation.active()) {
                existingPayments = existingPayments.add(obligation.monthlyPayment());
            }
        }

        if (monthlyIncome.signum() <= 0) {
            return new Result("insufficient_income_data", monthlyIncome, existingPayments, null);
        }
        BigDecimal share = existingPayments.add(proposedMonthlyPayment).movePointRight(2)
            .divide(monthlyIncome, MathContext.DECIMAL128);
        // Python rounds the binary floating-point quotient to one decimal place.
        BigDecimal rounded = new BigDecimal(share.doubleValue()).setScale(1, RoundingMode.HALF_EVEN);
        return new Result("calculated", monthlyIncome, existingPayments, rounded);
    }
}
