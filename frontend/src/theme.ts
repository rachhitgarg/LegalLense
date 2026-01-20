/**
 * theme.ts - Design tokens for Legal Lens UI
 *
 * Light, minimalistic design with optional dark mode.
 */

export const theme = {
    colors: {
        // Primary palette
        primary: '#2563eb',       // Blue-600
        primaryHover: '#1d4ed8',  // Blue-700
        primaryLight: '#dbeafe',  // Blue-100

        // Neutral palette
        background: '#ffffff',
        surface: '#f8fafc',       // Slate-50
        border: '#e2e8f0',        // Slate-200

        // Text
        textPrimary: '#0f172a',   // Slate-900
        textSecondary: '#475569', // Slate-600
        textMuted: '#94a3b8',     // Slate-400

        // Semantic
        success: '#10b981',       // Emerald-500
        warning: '#f59e0b',       // Amber-500
        error: '#ef4444',         // Red-500

        // Dark mode overrides
        dark: {
            background: '#0f172a',  // Slate-900
            surface: '#1e293b',     // Slate-800
            border: '#334155',      // Slate-700
            textPrimary: '#f8fafc', // Slate-50
            textSecondary: '#cbd5e1', // Slate-300
        },
    },

    typography: {
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        fontSize: {
            xs: '0.75rem',    // 12px
            sm: '0.875rem',   // 14px
            base: '1rem',     // 16px
            lg: '1.125rem',   // 18px
            xl: '1.25rem',    // 20px
            '2xl': '1.5rem',  // 24px
            '3xl': '1.875rem', // 30px
        },
        fontWeight: {
            light: 300,
            normal: 400,
            medium: 500,
            semibold: 600,
            bold: 700,
        },
    },

    spacing: {
        xs: '0.25rem',   // 4px
        sm: '0.5rem',    // 8px
        md: '1rem',      // 16px
        lg: '1.5rem',    // 24px
        xl: '2rem',      // 32px
        '2xl': '3rem',   // 48px
    },

    borderRadius: {
        sm: '0.25rem',   // 4px
        md: '0.5rem',    // 8px
        lg: '0.75rem',   // 12px
        xl: '1rem',      // 16px
        full: '9999px',
    },

    shadows: {
        sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
        md: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
        lg: '0 10px 15px -3px rgb(0 0 0 / 0.1)',
    },

    transitions: {
        fast: '150ms ease',
        normal: '200ms ease',
        slow: '300ms ease',
    },
};

export type Theme = typeof theme;
