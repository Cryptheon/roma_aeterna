import heapq

class Pathfinder:
    @staticmethod
    def find_path(world, start, end):
        # A* Implementation
        frontier = []
        heapq.heappush(frontier, (0, start))
        came_from = {start: None}
        cost_so_far = {start: 0}

        while frontier:
            _, current = heapq.heappop(frontier)
            if current == end: break

            cx, cy = current
            neighbors = [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]
            
            for nx, ny in neighbors:
                tile = world.get_tile(nx, ny)
                if tile and tile.is_walkable:
                    new_cost = cost_so_far[current] + tile.movement_cost
                    if (nx, ny) not in cost_so_far or new_cost < cost_so_far[(nx, ny)]:
                        cost_so_far[(nx, ny)] = new_cost
                        prio = new_cost + abs(end[0]-nx) + abs(end[1]-ny)
                        heapq.heappush(frontier, (prio, (nx, ny)))
                        came_from[(nx, ny)] = current
        
        # Reconstruct
        current = end
        path = []
        if end not in came_from: return []
        while current != start:
            path.append(current)
            current = came_from[current]
        path.reverse()
        return path
