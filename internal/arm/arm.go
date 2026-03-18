package arm

import (
	"fmt"
	"os"
	"path/filepath"
)

// Arm represents an experiment arm configuration
type Arm struct {
	Name       string
	LoadoutPath string
}

// ParseArm parses an arm specification from CLI arguments
// "vanilla" returns an empty loadout path
// Any other path is validated as an existing directory
func ParseArm(spec string) (Arm, error) {
	if spec == "vanilla" {
		return Arm{
			Name:        "vanilla",
			LoadoutPath: "",
		}, nil
	}

	// Check if path exists
	info, err := os.Stat(spec)
	if err != nil {
		if os.IsNotExist(err) {
			return Arm{}, fmt.Errorf("path does not exist: %s", spec)
		}
		return Arm{}, fmt.Errorf("error accessing path %s: %v", spec, err)
	}

	// Check if it's a directory
	if !info.IsDir() {
		return Arm{}, fmt.Errorf("path is not a directory: %s", spec)
	}

	// Extract directory name for the arm name
	name := filepath.Base(spec)

	return Arm{
		Name:        name,
		LoadoutPath: spec,
	}, nil
}
