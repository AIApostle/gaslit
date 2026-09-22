import { useEffect, useState } from "react";
import { getSwiftAgentConfig } from "../api";
import type { SwiftAgentConfig } from "../types";

export function useSwiftAgent() {
  const [config, setConfig] = useState<SwiftAgentConfig | null>(null);
  const [isLoaded, setIsLoaded] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function initWidget() {
      try {
        const cfg = await getSwiftAgentConfig();
        if (!mounted) return;
        setConfig(cfg);

        // Check if script is already present
        const existingScript = document.getElementById("swiftagents-widget-script");
        if (existingScript) {
          setIsLoaded(Boolean(window.SwiftAgentWidget?.isLoaded));
          return;
        }

        // Dynamically load script
        const script = document.createElement("script");
        script.id = "swiftagents-widget-script";
        script.src = cfg.widget_url || "https://widget.swiftagents.org/dist/widget-ui.js";
        script.dataset.companyId = cfg.company_id;
        script.dataset.apiKey = cfg.public_key;
        script.defer = true;

        script.onload = () => {
          if (mounted) {
            setIsLoaded(true);
          }
        };

        script.onerror = () => {
          if (mounted) {
            setError("Failed to load SwiftAgents widget script from CDN.");
          }
        };

        document.body.appendChild(script);
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : "Error initializing SwiftAgents widget");
        }
      }
    }

    initWidget();

    return () => {
      mounted = false;
    };
  }, []);

  const [pendingOpen, setPendingOpen] = useState(false);

  useEffect(() => {
    if (isLoaded && pendingOpen && window.SwiftAgentWidget) {
      window.SwiftAgentWidget.open();
      setPendingOpen(false);
    }
  }, [isLoaded, pendingOpen]);

  const openAgent = () => {
    if (window.SwiftAgentWidget) {
      window.SwiftAgentWidget.open();
    } else {
      setPendingOpen(true);
    }
  };

  const closeAgent = () => {
    if (window.SwiftAgentWidget) {
      window.SwiftAgentWidget.close();
    }
  };

  const toggleAgent = () => {
    if (window.SwiftAgentWidget) {
      window.SwiftAgentWidget.toggle();
    } else {
      setPendingOpen(true);
    }
  };

  return {
    config,
    isLoaded,
    error,
    openAgent,
    closeAgent,
    toggleAgent,
  };
}
