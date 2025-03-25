import React, { useState, useEffect } from 'react';

const VenueMap = () => {
    const [venues, setVenues] = useState([
        {
            id: 1,
            name: 'Mentone Grammar Playing Fields',
            address: 'Mentone, VIC',
            x: 150,
            y: 120,
            gamesCount: 8
        },
        {
            id: 2,
            name: 'State Netball Hockey Centre',
            address: 'Parkville, VIC',
            x: 50,
            y: 70,
            gamesCount: 4
        },
        {
            id: 3,
            name: 'Footscray Hockey Centre',
            address: 'Footscray, VIC',
            x: 30,
            y: 150,
            gamesCount: 2
        },
        {
            id: 4,
            name: 'Hawthorn Hockey Club',
            address: 'Hawthorn, VIC',
            x: 120,
            y: 60,
            gamesCount: 3
        },
        {
            id: 5,
            name: 'Doncaster Hockey Club',
            address: 'Doncaster, VIC',
            x: 200,
            y: 40,
            gamesCount: 1
        }
    ]);

    const [selectedVenue, setSelectedVenue] = useState(null);

    // Handle venue click
    const handleVenueClick = (venue) => {
        setSelectedVenue(venue);
    };

    // Close venue details
    const closeVenueDetails = () => {
        setSelectedVenue(null);
    };

    return (
        <div className="bg-white rounded-lg shadow p-4 w-full">
            <h2 className="text-xl font-semibold mb-4">Melbourne Hockey Venues</h2>

            <div className="relative" style={{ height: '400px', backgroundColor: '#edf2f7' }}>
                {/* Simple map */}
                <div className="absolute inset-0 p-4">
                    {/* Map features */}
                    <div className="absolute w-full h-full">
                        {/* Roads */}
                        <div className="absolute bg-gray-300" style={{ left: '50%', height: '100%', width: '10px', transform: 'translateX(-50%)' }}></div>
                        <div className="absolute bg-gray-300" style={{ top: '50%', width: '100%', height: '10px', transform: 'translateY(-50%)' }}></div>

                        {/* Water */}
                        <div className="absolute bg-blue-200 rounded-full" style={{ width: '80px', height: '80px', left: '70%', top: '70%' }}></div>

                        {/* City center */}
                        <div className="absolute bg-gray-400 rounded-lg" style={{ width: '40px', height: '40px', left: '45%', top: '45%' }}>
                            <div className="absolute inset-0 flex items-center justify-center text-xs font-bold">CBD</div>
                        </div>
                    </div>

                    {/* Venue markers */}
                    {venues.map((venue) => (
                        <div
                            key={venue.id}
                            className="absolute cursor-pointer transition-transform hover:scale-110"
                            style={{
                                left: `${venue.x}px`,
                                top: `${venue.y}px`
                            }}
                            onClick={() => handleVenueClick(venue)}
                        >
                            <div className="flex flex-col items-center">
                                <div
                                    className="bg-blue-600 rounded-full flex items-center justify-center text-white font-bold shadow-lg"
                                    style={{
                                        width: `${Math.max(30, venue.gamesCount * 6)}px`,
                                        height: `${Math.max(30, venue.gamesCount * 6)}px`
                                    }}
                                >
                                    {venue.gamesCount}
                                </div>
                                <div className="text-xs font-semibold mt-1 bg-white px-1 rounded shadow">
                                    {venue.name.split(' ')[0]}
                                </div>
                            </div>
                        </div>
                    ))}

                    {/* Legend */}
                    <div className="absolute bottom-2 left-2 bg-white p-2 rounded shadow text-xs">
                        <div className="font-semibold mb-1">Legend:</div>
                        <div className="flex items-center">
                            <div className="w-4 h-4 bg-blue-600 rounded-full mr-1"></div>
                            <span>Number of games</span>
                        </div>
                        <div className="flex items-center mt-1">
                            <div className="w-4 h-4 bg-gray-400 rounded-sm mr-1"></div>
                            <span>City center</span>
                        </div>
                    </div>
                </div>

                {/* Venue details popup */}
                {selectedVenue && (
                    <div className="absolute right-4 top-4 bg-white p-4 rounded-lg shadow-lg w-64 z-10">
                        <button
                            className="absolute top-2 right-2 text-gray-500 hover:text-gray-700"
                            onClick={closeVenueDetails}
                        >
                            &times;
                        </button>
                        <h3 className="font-bold text-lg mb-2">{selectedVenue.name}</h3>
                        <p className="text-gray-600 mb-2">{selectedVenue.address}</p>
                        <div className="bg-blue-100 p-2 rounded">
                            <p className="text-sm"><span className="font-semibold">{selectedVenue.gamesCount}</span> {selectedVenue.gamesCount === 1 ? 'game' : 'games'} scheduled</p>
                        </div>
                        <button className="mt-3 bg-blue-600 text-white py-1 px-3 rounded text-sm hover:bg-blue-700">
                            View Games
                        </button>
                    </div>
                )}
            </div>

            <div className="mt-4">
                <h3 className="font-medium mb-2">Upcoming Games by Venue</h3>
                <div className="space-y-2">
                    {venues.map(venue => (
                        <div
                            key={venue.id}
                            className="p-3 bg-gray-50 rounded hover:bg-gray-100 cursor-pointer flex justify-between items-center"
                            onClick={() => handleVenueClick(venue)}
                        >
                            <div>
                                <div className="font-medium">{venue.name}</div>
                                <div className="text-sm text-gray-500">{venue.address}</div>
                            </div>
                            <div className="bg-blue-100 text-blue-800 font-medium py-1 px-2 rounded-full text-sm">
                                {venue.gamesCount} {venue.gamesCount === 1 ? 'game' : 'games'}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default VenueMap;