import React, { useState, useEffect, useRef } from 'react';
import Keyboard from 'react-simple-keyboard';
import 'react-simple-keyboard/build/css/index.css';
import { X } from 'lucide-react';

interface VirtualKeyboardProps {
  onHeightChange?: (height: number) => void;
}

export function VirtualKeyboard({ onHeightChange }: VirtualKeyboardProps) {
  const [inputName, setInputName] = useState<string>('default');
  const [layoutName, setLayoutName] = useState<string>('default');
  const [visible, setVisible] = useState<boolean>(false);
  const [inputValue, setInputValue] = useState<string>('');
  
  const keyboardRef = useRef<any>(null);
  const activeInputRef = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Notify parent of height changes
  useEffect(() => {
    if (onHeightChange) {
      if (visible && containerRef.current) {
        // Obter altura atual do teclado e notificar parent
        onHeightChange(containerRef.current.offsetHeight);
      } else {
        onHeightChange(0);
      }
    }
  }, [visible, onHeightChange]);

  useEffect(() => {
    const handleFocus = (event: Event) => {
      const target = event.target as HTMLElement;
      if (
        target.tagName === 'INPUT' || 
        target.tagName === 'TEXTAREA'
      ) {
        const input = target as HTMLInputElement | HTMLTextAreaElement;
        // Ignore inputs that are read-only or hidden
        if (input.readOnly || input.type === 'hidden' || input.type === 'submit' || input.type === 'button') {
          return;
        }
        
        activeInputRef.current = input;
        setInputValue(input.value);
        setVisible(true);
        
        // Se o input não tem id ou name, atribuímos um temporário para o teclado trackear
        const name = input.id || input.name || 'temp-input';
        setInputName(name);
        
        if (keyboardRef.current) {
          keyboardRef.current.setInput(input.value);
        }

        // Scroll input into view after keyboard animation/render
        setTimeout(() => {
          if (activeInputRef.current) {
            activeInputRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
        }, 300);
      }
    };

    const handleBlur = (event: FocusEvent) => {
      // Pequeno delay para permitir o click nas teclas do teclado virtual sem fechá-lo
      setTimeout(() => {
        const activeEl = document.activeElement;
        // Se o elemento ativo for algo dentro do teclado (se houver tabindex)
        // Ou se clicar fora
        const isKeyboardInteraction = activeEl && activeEl.closest('.virtual-keyboard-container');
        
        if (!isKeyboardInteraction) {
          // Não escondemos imediatamente no blur porque o click na tela
          // de touch tira o foco do input original para clicar na tecla virtual.
        }
      }, 100);
    };
    
    // Adicionamos um click listener no window para esconder quando clica fora
    const handleWindowClick = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA';
      const isKeyboard = target.closest('.virtual-keyboard-container');
      
      if (!isInput && !isKeyboard && visible) {
        setVisible(false);
      }
    };

    document.addEventListener('focusin', handleFocus);
    document.addEventListener('focusout', handleBlur);
    document.addEventListener('mousedown', handleWindowClick);

    return () => {
      document.removeEventListener('focusin', handleFocus);
      document.removeEventListener('focusout', handleBlur);
      document.removeEventListener('mousedown', handleWindowClick);
    };
  }, [visible]);

  // Sincroniza quando o valor original do input muda por React
  useEffect(() => {
    const interval = setInterval(() => {
      if (activeInputRef.current && visible) {
        const currentVal = activeInputRef.current.value;
        if (currentVal !== inputValue) {
          setInputValue(currentVal);
          if (keyboardRef.current) {
            keyboardRef.current.setInput(currentVal);
          }
        }
      }
    }, 500);
    return () => clearInterval(interval);
  }, [inputValue, visible]);

  const onChange = (input: string) => {
    setInputValue(input);
    
    if (activeInputRef.current) {
      // A mágica para o React registrar a mudança em um input controlado via código
      const el = activeInputRef.current;
      const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype,
        'value'
      )?.set;
      
      const nativeTextareaValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype,
        'value'
      )?.set;

      if (el.tagName === 'INPUT' && nativeInputValueSetter) {
        nativeInputValueSetter.call(el, input);
      } else if (el.tagName === 'TEXTAREA' && nativeTextareaValueSetter) {
        nativeTextareaValueSetter.call(el, input);
      }

      const ev2 = new Event('input', { bubbles: true });
      el.dispatchEvent(ev2);
    }
  };

  const onKeyPress = (button: string) => {
    if (button === "{shift}" || button === "{lock}") {
      setLayoutName(layoutName === "default" ? "shift" : "default");
    }
    if (button === "{enter}") {
      setVisible(false);
    }
  };

  if (!visible) return null;

  return (
    <div ref={containerRef} className="virtual-keyboard-container fixed bottom-0 left-0 w-full z-[9999] p-4 bg-zinc-900/95 backdrop-blur-xl border-t border-white/10 shadow-[0_-10px_40px_rgba(0,0,0,0.5)] flex flex-col items-center animate-in slide-in-from-bottom-full duration-300">
      <div className="w-full max-w-4xl relative">
        <button 
          onClick={() => setVisible(false)}
          className="absolute -top-12 right-0 bg-white/10 hover:bg-white/20 text-white rounded-full p-2 backdrop-blur-md border border-white/10 transition-all"
        >
          <X className="w-5 h-5" />
        </button>
        <div className="text-black rounded-xl overflow-hidden shadow-2xl">
          <Keyboard
            keyboardRef={r => (keyboardRef.current = r)}
            layoutName={layoutName}
            onChange={onChange}
            onKeyPress={onKeyPress}
            inputName={inputName}
            theme={"hg-theme-default hg-layout-default my-custom-keyboard"}
            layout={{
              default: [
                "` 1 2 3 4 5 6 7 8 9 0 - = {bksp}",
                "q w e r t y u i o p [ ] \\",
                "{lock} a s d f g h j k l ; ' {enter}",
                "{shift} z x c v b n m , . / {shift}",
                ".com @ {space}"
              ],
              shift: [
                "~ ! @ # $ % ^ & * ( ) _ + {bksp}",
                "Q W E R T Y U I O P { } |",
                "{lock} A S D F G H J K L : \" {enter}",
                "{shift} Z X C V B N M < > ? {shift}",
                ".com @ {space}"
              ]
            }}
            display={{
              '{bksp}': '⌫ apagar',
              '{enter}': '↵ fechar',
              '{shift}': '⇧',
              '{lock}': 'Caps',
              '{space}': ' '
            }}
          />
        </div>
      </div>
      <style>{`
        .my-custom-keyboard {
          background-color: #18181b !important;
          border-radius: 12px;
          padding: 10px;
        }
        .hg-button {
          background: #27272a !important;
          color: white !important;
          border-bottom: 2px solid #3f3f46 !important;
          border-radius: 8px !important;
          font-weight: 500;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
        }
        .hg-button:active {
          background: #3f3f46 !important;
          border-bottom-width: 0px !important;
          transform: translateY(2px);
        }
        .hg-button.hg-standardBtn {
          font-size: 1.1rem;
        }
      `}</style>
    </div>
  );
}
