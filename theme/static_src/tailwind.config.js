/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        '../../templates/**/*.html',
        '../../**/templates/**/*.html',
        '../../**/forms.py',  // To scan classes in Python forms
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
            },
            colors: {
                'core-green': '#064E3B',    /* Deep Ethiopian Green */
                'core-teal': '#065F46',     /* Secondary Green */
                'core-gold': '#F59E0B',     /* Ethiopian Gold */
                'core-gold-light': '#FEF3C7',
                'surface': '#FAFAFA',       /* Light Gray Background */
                // Mappings for the landing page compatibility
                'ethio-green-900': '#064E3B',
                'ethio-green-800': '#065F46',
                'ethio-green-500': '#10B981',
                'ethio-gold': '#F59E0B',
                'ethio-gold-dark': '#D97706',
                'ethio-white': '#F9FAFB',
            },
            boxShadow: {
                'glass': '0 8px 32px 0 rgba(31, 38, 135, 0.07)',
                'float': '0 20px 50px -12px rgba(6, 78, 59, 0.25)',
                'soft': '0 20px 40px -10px rgba(0, 0, 0, 0.05)',
                'glow': '0 0 20px rgba(245, 158, 11, 0.15)',
            },
            animation: {
                'blob': 'blob 7s infinite',
                'slide-up': 'slideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards',
                'fade-in': 'fadeIn 0.5s ease-out forwards',
            },
            keyframes: {
                blob: {
                    '0%': { transform: 'translate(0px, 0px) scale(1)' },
                    '33%': { transform: 'translate(30px, -50px) scale(1.1)' },
                    '66%': { transform: 'translate(-20px, 20px) scale(0.9)' },
                    '100%': { transform: 'translate(0px, 0px) scale(1)' },
                },
                slideUp: {
                    '0%': { transform: 'translateY(100%)' },
                    '100%': { transform: 'translateY(0)' },
                },
                fadeIn: {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                }
            }
        },
    },
    plugins: [
        require('@tailwindcss/forms'),
        require('@tailwindcss/typography'),
        require('@tailwindcss/aspect-ratio'),
    ],
}