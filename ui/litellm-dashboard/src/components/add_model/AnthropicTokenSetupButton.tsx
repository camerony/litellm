import { Button, Modal, Input, Typography, Space, Alert } from "antd";
import { KeyOutlined, CheckCircleOutlined, InfoCircleOutlined } from "@ant-design/icons";
import React, { useState } from "react";

const { Text, Title, Paragraph, Link } = Typography;
const { TextArea } = Input;

interface AnthropicTokenSetupButtonProps {
  onSuccess?: (data: { token: string; profile_id: string }) => void;
}

const AnthropicTokenSetupButton: React.FC<AnthropicTokenSetupButtonProps> = ({ onSuccess }) => {
  const [modalVisible, setModalVisible] = useState(false);
  const [token, setToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const validateToken = (token: string): string | null => {
    const trimmed = token.trim();

    if (!trimmed) {
      return "Token cannot be empty";
    }

    if (trimmed.length < 20) {
      return "Token too short (minimum 20 characters)";
    }

    if (/\s/.test(trimmed)) {
      return "Token contains invalid whitespace";
    }

    return null;
  };

  const handleSetupToken = async () => {
    setError(null);
    const validationError = validateToken(token);

    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);

    try {
      // Call backend API to store the token
      const response = await fetch("/anthropic/setup-token", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token: token.trim(),
          profile_id: "anthropic:manual"
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Failed to store token: ${response.statusText}`);
      }

      const data = await response.json();

      setSuccess(true);
      setError(null);

      // Call success callback
      if (onSuccess) {
        onSuccess({
          token: token.trim(),
          profile_id: data.profile_id || "anthropic:manual"
        });
      }

      // Close modal after brief delay
      setTimeout(() => {
        setModalVisible(false);
        setSuccess(false);
        setToken("");
      }, 2000);

    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to store token");
    } finally {
      setLoading(false);
    }
  };

  const openModal = () => {
    setModalVisible(true);
    setError(null);
    setSuccess(false);
    setToken("");
  };

  return (
    <>
      <Button
        type="primary"
        icon={<KeyOutlined />}
        onClick={openModal}
        size="large"
        style={{ width: "100%" }}
      >
        Setup Anthropic Token (claude setup-token)
      </Button>

      <Modal
        title={
          <Space>
            <KeyOutlined />
            <span>Anthropic Token Setup</span>
          </Space>
        }
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setModalVisible(false)}>
            Cancel
          </Button>,
          <Button
            key="submit"
            type="primary"
            loading={loading}
            onClick={handleSetupToken}
            disabled={success}
          >
            {success ? "Saved!" : "Save Token"}
          </Button>,
        ]}
        width={700}
      >
        <Space direction="vertical" size="large" style={{ width: "100%" }}>
          {/* Instructions */}
          <Alert
            message="Setup Instructions"
            description={
              <Space direction="vertical" size="small">
                <Text>
                  This uses tokens from Anthropic's official Claude CLI - the same method as OpenClaw.
                </Text>
                <ol style={{ marginLeft: 20, marginTop: 10 }}>
                  <li>
                    Install Claude CLI:{" "}
                    <Text code>npm install -g @anthropic-ai/claude-cli</Text>
                  </li>
                  <li>
                    Run: <Text code>claude setup-token</Text>
                  </li>
                  <li>Copy the token it generates</li>
                  <li>Paste it below</li>
                </ol>
              </Space>
            }
            type="info"
            icon={<InfoCircleOutlined />}
            showIcon
          />

          {/* Token Input */}
          <div>
            <Text strong>Paste your setup-token:</Text>
            <TextArea
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Paste token from `claude setup-token` here..."
              rows={4}
              style={{ marginTop: 8, fontFamily: "monospace", fontSize: 12 }}
              status={error ? "error" : undefined}
            />
            {error && (
              <Text type="danger" style={{ marginTop: 4, display: "block" }}>
                {error}
              </Text>
            )}
          </div>

          {/* Success Message */}
          {success && (
            <Alert
              message="Token Saved Successfully!"
              description="You can now use Anthropic models with your Claude subscription."
              type="success"
              icon={<CheckCircleOutlined />}
              showIcon
            />
          )}

          {/* Benefits */}
          <div>
            <Text strong>Benefits vs API Keys:</Text>
            <ul style={{ marginLeft: 20, marginTop: 8 }}>
              <li>No API key management needed</li>
              <li>Uses your Claude subscription directly</li>
              <li>Same authentication as Claude CLI</li>
              <li>Compatible with OpenClaw workflows</li>
            </ul>
          </div>

          {/* Documentation Link */}
          <Alert
            message={
              <span>
                📚{" "}
                <Link
                  href="https://docs.openclaw.ai/providers/anthropic"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Learn more about token-based authentication
                </Link>
              </span>
            }
            type="info"
            showIcon={false}
          />
        </Space>
      </Modal>
    </>
  );
};

export default AnthropicTokenSetupButton;
