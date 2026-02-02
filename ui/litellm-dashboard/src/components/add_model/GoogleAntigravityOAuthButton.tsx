import { Button, message } from "antd";
import { GoogleOutlined } from "@ant-design/icons";
import React, { useEffect, useCallback } from "react";

interface GoogleAntigravityOAuthButtonProps {
    onSuccess?: (data: { email: string; provider: string }) => void;
    onError?: (error: string) => void;
}

const GoogleAntigravityOAuthButton: React.FC<GoogleAntigravityOAuthButtonProps> = ({
    onSuccess,
    onError,
}) => {
    const [loading, setLoading] = React.useState(false);

    const handleMessage = useCallback(
        (event: MessageEvent) => {
            // Validate the message is from our OAuth popup
            if (event.data && typeof event.data === "object" && "provider" in event.data) {
                if (event.data.provider === "google_antigravity") {
                    setLoading(false);
                    if (event.data.success) {
                        message.success(`Connected as ${event.data.email}`);
                        onSuccess?.({ email: event.data.email, provider: "google_antigravity" });
                    } else {
                        message.error(`Authentication failed: ${event.data.error}`);
                        onError?.(event.data.error);
                    }
                }
            }
        },
        [onSuccess, onError]
    );

    useEffect(() => {
        window.addEventListener("message", handleMessage);
        return () => {
            window.removeEventListener("message", handleMessage);
        };
    }, [handleMessage]);

    const handleClick = () => {
        setLoading(true);

        // Open OAuth popup
        const width = 600;
        const height = 700;
        const left = window.screenX + (window.outerWidth - width) / 2;
        const top = window.screenY + (window.outerHeight - height) / 2;

        const popup = window.open(
            "/auth/google_antigravity/init",
            "Google Antigravity Login",
            `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`
        );

        // Check if popup was blocked
        if (!popup || popup.closed || typeof popup.closed === "undefined") {
            setLoading(false);
            message.error("Please allow popups for this site to authenticate");
            onError?.("Popup blocked");
        }

        // Monitor popup close
        const checkClosed = setInterval(() => {
            if (popup && popup.closed) {
                clearInterval(checkClosed);
                setLoading(false);
            }
        }, 500);
    };

    return (
        <div className="mb-4">
            <Button
                type="primary"
                icon={<GoogleOutlined />}
                onClick={handleClick}
                loading={loading}
                size="large"
                style={{
                    background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                    border: "none",
                    height: "48px",
                    fontSize: "16px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "8px",
                }}
            >
                {loading ? "Connecting..." : "Connect with Google"}
            </Button>
            <p className="text-sm text-gray-500 mt-2">
                Authenticate to use Claude and Gemini models via Google&apos;s Antigravity API.
            </p>
        </div>
    );
};

export default GoogleAntigravityOAuthButton;
