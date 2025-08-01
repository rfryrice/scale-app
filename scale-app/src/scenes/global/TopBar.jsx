import { Box, IconButton, Menu, MenuItem, useTheme } from "@mui/material";
import { useContext, useState } from "react";
import { ColorModeContext, tokens } from "../../theme";
import InputBase from "@mui/material/InputBase";
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined";
import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined";
import NotificationsOutlinedIcon from "@mui/icons-material/NotificationsOutlined";
import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined";
import PersonOutlinedIcon from "@mui/icons-material/PersonOutlined";
import SearchIcon from "@mui/icons-material/Search";
import MenuIcon from "@mui/icons-material/Menu";

const TopBar = ({ setIsSidebar, onDrawerOpen, username, onLogout }) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const handleMenu = (event) => setAnchorEl(event.currentTarget);
  const handleClose = () => setAnchorEl(null);
  const theme = useTheme();
  const colors = tokens(theme.palette.mode);
  const colorMode = useContext(ColorModeContext);

  return (
    <Box display="flex" justifyContent="space-between" p={2}>
      {/* SEARCH BAR */}
      <Box
        display="flex"
        backgroundColor={colors.primary[800]}
        borderRadius="3px"
      >
        <Box>
          {/* DRAWER BUTTON */}
          <IconButton
            color="inherit"
            aria-label="open drawer"
            onClick={onDrawerOpen}
          >
            <MenuIcon />
          </IconButton>
        </Box>

        <InputBase sx={{ ml: 2, flex: 1 }} placeholder="Search" />
        <IconButton type="button" sx={{ p: 1 }}>
          <SearchIcon />
        </IconButton>
      </Box>

      {/* ICONS */}
      <Box display="flex">
        <IconButton
          color="inherit"
          onClick={async () => {
            try {
              const res = await fetch(
                `${import.meta.env.VITE_API_URL}/git/pull`,
                { method: "POST" }
              );
              const data = await res.json();
              alert(
                data.success
                  ? `Git Pull Success:\n${data.output}`
                  : `Git Pull Failed:\n${data.error}`
              );
            } catch (err) {
              alert("Error running git pull");
            }
          }}
        >
          <NotificationsOutlinedIcon />
        </IconButton>
        <IconButton onClick={colorMode.toggleColorMode}>
          {theme.palette.mode === "dark" ? (
            <DarkModeOutlinedIcon />
          ) : (
            <LightModeOutlinedIcon />
          )}
        </IconButton>
        <IconButton>
          <SettingsOutlinedIcon />
        </IconButton>
        <IconButton color="inherit" onClick={handleMenu}>
          <PersonOutlinedIcon />
        </IconButton>
        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={handleClose}
        >
          <MenuItem disabled>{username}</MenuItem>
          <MenuItem
            onClick={() => {
              handleClose();
              onLogout();
            }}
          >
            Log out
          </MenuItem>
        </Menu>
      </Box>
    </Box>
  );
};

export default TopBar;
