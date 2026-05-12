import { useState } from "react";
import { loadStripe } from "@stripe/stripe-js";
import { Elements, CardElement, useStripe, useElements } from "@stripe/react-stripe-js";
import { API } from "../api";
import { useLanguage } from "../context/LanguageContext";
import "../pages/PlanAccess.css";

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY);

function CheckoutForm({ amount, onSuccess, onError }) {
  const stripe = useStripe();
  const elements = useElements();
  const { t } = useLanguage();
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!stripe || !elements) {
      setErrorMessage(t("paymentSystemLoading"));
      return;
    }

    setLoading(true);
    setErrorMessage(null);

    try {
      const response = await API.post("/api/create-payment-intent", {
        amount: Math.round(amount * 100),
        currency: "eur",
      });

      const { clientSecret } = response.data;

      const { error: confirmError, paymentIntent } = await stripe.confirmCardPayment(clientSecret, {
        payment_method: {
          card: elements.getElement(CardElement),
        },
      });

      if (confirmError) {
        setErrorMessage(t("paymentFailed"));
        onError?.(confirmError);
      } else if (paymentIntent?.status === "succeeded") {
        onSuccess?.(paymentIntent);
      }
    } catch (error) {
      setErrorMessage(t("paymentFailed"));
      onError?.(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="stripe-card-element">
        <CardElement
          options={{
            style: {
              base: {
                fontSize: "16px",
                color: "#424770",
                "::placeholder": {
                  color: "#aab7c4",
                },
              },
              invalid: {
                color: "#9e2146",
              },
            },
            hidePostalCode: true,
          }}
        />
      </div>

      {errorMessage && (
        <div className="stripe-error-message">
          {errorMessage}
        </div>
      )}

      <div className="stripe-button-wrapper">
        <button
          type="submit"
          disabled={!stripe || loading}
          className="stripe-pay-btn"
        >
          {loading ? t("processing") : `${t("pay")} ${amount.toFixed(2).replace(".", ",")} €`}
        </button>
      </div>
    </form>
  );
}

export default function StripePayment({ amount, onSuccess, onError }) {
  const { t, language } = useLanguage();

  if (!import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY) {
    return (
      <div className="stripe-error-container">
        {t("stripeMissing")}
      </div>
    );
  }

  return (
    <Elements
      key={language}
      stripe={stripePromise}
      options={{ locale: language === "en" ? "en" : "lt" }}
    >
      <CheckoutForm amount={amount} onSuccess={onSuccess} onError={onError} />
    </Elements>
  );
}
