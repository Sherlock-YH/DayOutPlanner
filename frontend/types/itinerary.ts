export interface Location {
  lat: number;
  lng: number;
}

export interface ItineraryStop {
  id?: string;
  name: string;
  location?: Location;
  lat?: number;
  lng?: number;
  address?: string;
  description?: string;
  time?: string;
  category?: string;
  [key: string]: any; // Allows flexible extension
}