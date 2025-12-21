import { useState, useEffect, useRef } from 'react';
import { Input } from './ui/input';
import { MapPin, Loader2 } from 'lucide-react';

const GOOGLE_PLACES_API_KEY = process.env.REACT_APP_GOOGLE_PLACES_API_KEY;

export default function AddressAutocomplete({ value, onChange, placeholder, className, ...props }) {
  const [inputValue, setInputValue] = useState(value || '');
  const [suggestions, setSuggestions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isScriptLoaded, setIsScriptLoaded] = useState(false);
  const autocompleteService = useRef(null);
  const placesService = useRef(null);
  const containerRef = useRef(null);

  // Load Google Places script
  useEffect(() => {
    if (!GOOGLE_PLACES_API_KEY) {
      console.warn('Google Places API key not configured');
      return;
    }

    if (window.google?.maps?.places) {
      setIsScriptLoaded(true);
      return;
    }

    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_PLACES_API_KEY}&libraries=places`;
    script.async = true;
    script.defer = true;
    script.onload = () => setIsScriptLoaded(true);
    script.onerror = () => console.error('Failed to load Google Places script');
    document.head.appendChild(script);

    return () => {
      // Cleanup if needed
    };
  }, []);

  // Initialize services when script is loaded
  useEffect(() => {
    if (isScriptLoaded && window.google?.maps?.places) {
      autocompleteService.current = new window.google.maps.places.AutocompleteService();
      // Create a dummy div for PlacesService (required by the API)
      const dummyElement = document.createElement('div');
      placesService.current = new window.google.maps.places.PlacesService(dummyElement);
    }
  }, [isScriptLoaded]);

  // Update input when value prop changes
  useEffect(() => {
    setInputValue(value || '');
  }, [value]);

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const fetchSuggestions = async (input) => {
    if (!input || input.length < 3 || !autocompleteService.current) {
      setSuggestions([]);
      return;
    }

    setIsLoading(true);

    try {
      const request = {
        input,
        componentRestrictions: { country: 'us' }, // Restrict to US addresses
        types: ['address']
      };

      autocompleteService.current.getPlacePredictions(request, (predictions, status) => {
        setIsLoading(false);
        if (status === window.google.maps.places.PlacesServiceStatus.OK && predictions) {
          setSuggestions(predictions.slice(0, 5)); // Limit to 5 suggestions
          setShowSuggestions(true);
        } else {
          setSuggestions([]);
        }
      });
    } catch (error) {
      console.error('Error fetching suggestions:', error);
      setIsLoading(false);
      setSuggestions([]);
    }
  };

  const handleInputChange = (e) => {
    const newValue = e.target.value;
    setInputValue(newValue);
    onChange(newValue);
    fetchSuggestions(newValue);
  };

  const handleSelectSuggestion = (suggestion) => {
    // Get place details for the full address
    if (placesService.current) {
      placesService.current.getDetails(
        { placeId: suggestion.place_id, fields: ['formatted_address', 'address_components'] },
        (place, status) => {
          if (status === window.google.maps.places.PlacesServiceStatus.OK && place) {
            const formattedAddress = place.formatted_address || suggestion.description;
            setInputValue(formattedAddress);
            onChange(formattedAddress);
          } else {
            setInputValue(suggestion.description);
            onChange(suggestion.description);
          }
          setSuggestions([]);
          setShowSuggestions(false);
        }
      );
    } else {
      setInputValue(suggestion.description);
      onChange(suggestion.description);
      setSuggestions([]);
      setShowSuggestions(false);
    }
  };

  // If no API key, render a regular input
  if (!GOOGLE_PLACES_API_KEY) {
    return (
      <Input
        value={inputValue}
        onChange={(e) => {
          setInputValue(e.target.value);
          onChange(e.target.value);
        }}
        placeholder={placeholder}
        className={className}
        {...props}
      />
    );
  }

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <Input
          value={inputValue}
          onChange={handleInputChange}
          onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
          placeholder={placeholder || "Start typing an address..."}
          className={`pr-8 ${className || ''}`}
          autoComplete="off"
          {...props}
        />
        <div className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400">
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <MapPin className="w-4 h-4" />
          )}
        </div>
      </div>

      {/* Suggestions dropdown */}
      {showSuggestions && suggestions.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg max-h-60 overflow-auto">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion.place_id}
              type="button"
              className="w-full px-3 py-2 text-left text-sm hover:bg-slate-50 focus:bg-slate-50 focus:outline-none flex items-start gap-2 border-b border-slate-100 last:border-0"
              onClick={() => handleSelectSuggestion(suggestion)}
            >
              <MapPin className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
              <div>
                <div className="font-medium text-slate-900">
                  {suggestion.structured_formatting?.main_text || suggestion.description}
                </div>
                {suggestion.structured_formatting?.secondary_text && (
                  <div className="text-xs text-slate-500">
                    {suggestion.structured_formatting.secondary_text}
                  </div>
                )}
              </div>
            </button>
          ))}
          <div className="px-3 py-1.5 text-xs text-slate-400 bg-slate-50 flex items-center gap-1">
            <img 
              src="https://www.gstatic.com/images/branding/googlelogo/2x/googlelogo_color_74x24dp.png" 
              alt="Google" 
              className="h-3"
            />
            <span>Powered by Google</span>
          </div>
        </div>
      )}
    </div>
  );
}
