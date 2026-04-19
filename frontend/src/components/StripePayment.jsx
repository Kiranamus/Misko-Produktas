import { useState } from "react";
import { loadStripe } from "@stripe/stripe-js";
import { Elements, CardElement, useStripe, useElements } from "@stripe/react-stripe-js";
import { API } from "../api";
import "../pages/PlanAccess.css";

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY);

function CheckoutForm({ amount, onSuccess, onError }) {
  const stripe = useStripe();
  const elements = useElements();
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    
    if (!stripe || !elements) {
      setErrorMessage("Mokėjimo sistema dar nėra pasiruošusi. Palaukite momentą.");
      return;
    }

    setLoading(true);
    setErrorMessage(null);

    try {
      console.log("Creating payment intent for amount:", amount);
      const response = await API.post("/api/create-payment-intent", {
        amount: Math.round(amount * 100),
        currency: "eur"
      });

      const { clientSecret } = response.data;
      console.log("Client secret received");

      const { error: confirmError, paymentIntent } = await stripe.confirmCardPayment(clientSecret, {
        payment_method: {
          card: elements.getElement(CardElement),
        },
      });

      if (confirmError) {
        console.error("Payment error:", confirmError);
        setErrorMessage(confirmError.message);
        onError?.(confirmError);
      } else if (paymentIntent?.status === "succeeded") {
        console.log("Payment successful:", paymentIntent);
        onSuccess?.(paymentIntent);
      }
    } catch (err) {
      console.error("Error:", err);
      setErrorMessage(err.response?.data?.detail || err.message || "Klaida apdorojant mokėjimą");
      onError?.(err);
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
          {loading ? "Apdorojama..." : `Mokėti ${amount.toFixed(2)} €`}
        </button>
      </div>
    </form>
  );
}

export default function StripePayment({ amount, onSuccess, onError }) {
  if (!import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY) {
    console.error("Stripe publishable key is missing!");
    return (
      <div style={{ color: "red", textAlign: "center", padding: "20px" }}>
        Klaida: Trūksta Stripe raktų. Pridėkite VITE_STRIPE_PUBLISHABLE_KEY į .env failą.
      </div>
    );
  }

  return (
    <Elements stripe={stripePromise}>
      <CheckoutForm amount={amount} onSuccess={onSuccess} onError={onError} />
    </Elements>
  );
}