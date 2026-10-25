from dataclasses import dataclass

from app.llm.base import BaseLLM


@dataclass
class LocalResponse:

    content: str


class LocalProvider(BaseLLM):

    def invoke(self, prompt: str):

        text = prompt.lower()
        question = text.rsplit("question:", 1)[-1]
        history = ""

        if "conversation history:" in text and "question:" in text:
            history = text.split(
                "conversation history:",
                1
            )[1].rsplit(
                "question:",
                1
            )[0]

        if "should a human review it" in text:
            return LocalResponse(content="NO")

        if "choose one agent" in text:
            if any(
                word in question
                for word in [
                    "it",
                    "that",
                    "same",
                    "again"
                ]
            ):
                if "reservation created successfully" in history:
                    return LocalResponse(content="reservation")

                if "parking price" in history:
                    return LocalResponse(content="pricing")

            if any(
                word in question
                for word in [
                    "reserve",
                    "reservation",
                    "book",
                    "spot"
                ]
            ):
                return LocalResponse(content="reservation")

            if any(
                word in question
                for word in [
                    "price",
                    "pricing",
                    "cost",
                    "fee",
                    "rate"
                ]
            ):
                return LocalResponse(content="pricing")

            return LocalResponse(content="support")

        # Handle RAG-enhanced agent prompts
        if "parking pricing assistant" in text:
            if "price" in question or "cost" in question or "fee" in question:
                return LocalResponse(content="Based on our pricing policy, standard weekday parking is $12 per day. Weekend rates are $15 per day, and holiday rates are $20 per day. Hourly rates start at $3 for the first hour.")
            return LocalResponse(content="For detailed pricing information, please refer to our pricing policy which covers weekday, weekend, holiday, hourly, and monthly rates.")

        if "parking reservation assistant" in text:
            if "cancel" in question:
                return LocalResponse(content="You can cancel reservations for free up to 24 hours before your scheduled time. Cancellations 2-24 hours before receive a 50% refund. No refunds are available for cancellations less than 2 hours before.")
            if "book" in question or "make" in question:
                return LocalResponse(content="To make a reservation, use our mobile app or website, select your location and time, enter vehicle information, and complete payment. You'll receive a QR code for entry.")
            return LocalResponse(content="Our reservation system allows you to book daily, monthly, and event parking. Free cancellations are available up to 24 hours before your reservation time.")

        if "parking support assistant" in text:
            if "operating hours" in question or "hours" in question:
                return LocalResponse(content="Our parking facilities are open 24 hours a day, 7 days a week, including holidays.")
            if "payment" in question or "pay" in question:
                return LocalResponse(content="We accept credit/debit cards at all kiosks, mobile app payments, and cash at designated locations. Monthly billing is available for contract holders.")
            return LocalResponse(content="I can help with information about our parking policies, facilities, payment methods, and general support inquiries.")

        return LocalResponse(content="I apologize, but I couldn't process that request. Please try rephrasing your question.")
